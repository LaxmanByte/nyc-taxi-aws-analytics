"""
================================================================================
CALL BOOKER — MAIN LAMBDA FUNCTION  v1.0
================================================================================
Trigger  : Twilio SMS webhook (POST via API Gateway)
Flow     : Inbound SMS → DynamoDB session → Claude Bedrock → reply SMS
           When all 4 fields collected:
             • Owner gets structured summary SMS  (Twilio)
             • Customer gets Calendly link SMS    (Twilio)
             • Owner gets email fallback          (SES, parallel via threading)
Model    : us.anthropic.claude-sonnet-4-20250514-v1:0
State    : DynamoDB  table = CALL_BOOKER_TABLE_NAME  (TTL 24 h)
================================================================================

Required Environment Variables
--------------------------------
TWILIO_ACCOUNT_SID      – Twilio account SID
TWILIO_AUTH_TOKEN       – Twilio auth token
TWILIO_FROM_NUMBER      – your Twilio phone number  e.g. +18005551234
OWNER_PHONE             – owner's cell for summary SMS
OWNER_EMAIL             – owner's email for SES fallback
SENDER_EMAIL            – verified SES sender address
CALENDLY_LINK           – your Calendly booking URL
CALL_BOOKER_TABLE_NAME  – DynamoDB table name
BEDROCK_REGION          – AWS region for Bedrock  e.g. us-east-1

DynamoDB Table Schema
--------------------------------
PK (S)                : customer phone number  e.g. +15125559999
conversation_history  : list  – [{role, content}, …]
collected             : map   – {name, zip, issue, preferred_time}
complete              : bool
created_at            : number (epoch)
ttl                   : number (epoch + 86400)
"""

import json
import os
import time
import threading
import logging
from urllib.parse import parse_qs

import boto3
from botocore.exceptions import ClientError
from twilio.rest import Client as TwilioClient
from twilio.twiml.messaging_response import MessagingResponse

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

TWILIO_ACCOUNT_SID  = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN   = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_FROM_NUMBER  = os.environ["TWILIO_FROM_NUMBER"]
OWNER_PHONE         = os.environ["OWNER_PHONE"]
OWNER_EMAIL         = os.environ["OWNER_EMAIL"]
SENDER_EMAIL        = os.environ["SENDER_EMAIL"]
CALENDLY_LINK       = os.environ["CALENDLY_LINK"]
TABLE_NAME          = os.environ["CALL_BOOKER_TABLE_NAME"]
BEDROCK_REGION      = os.environ.get("BEDROCK_REGION", "us-east-1")
MODEL_ID            = "us.anthropic.claude-sonnet-4-20250514-v1:0"
SESSION_TTL_SECONDS = 86_400  # 24 hours

# AWS clients (instantiated once per container)
dynamodb  = boto3.resource("dynamodb")
table     = dynamodb.Table(TABLE_NAME)
bedrock   = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
ses       = boto3.client("ses")
twilio_cl = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """
You are a friendly, professional SMS assistant for an HVAC company.
Your job is to collect four pieces of information from a customer who missed a call,
then confirm their details.

Information to collect (in order, one question at a time):
  1. Full name
  2. ZIP code (5-digit US ZIP)
  3. HVAC issue / reason for calling  (brief description)
  4. Preferred appointment time       (e.g. "Tuesday morning", "any weekday after 3pm")

Rules:
- Ask ONE question per message. Keep replies under 160 characters when possible.
- Be warm and concise.
- If the customer gives multiple answers at once, accept them all and ask only
  for whatever is still missing.
- Once all four fields are confirmed, reply ONLY with a valid JSON object in this
  exact shape — no extra text before or after it:
  {
    "complete": true,
    "name": "<value>",
    "zip": "<value>",
    "issue": "<value>",
    "preferred_time": "<value>",
    "reply": "<friendly closing SMS to send to the customer>"
  }
- While collecting data, reply ONLY with a plain conversational SMS string.
  Never output JSON until all four fields are confirmed.
- Do not ask for payment info, personal health info, or anything beyond the four fields.
"""

# ---------------------------------------------------------------------------
# DynamoDB session helpers
# ---------------------------------------------------------------------------

def load_session(phone: str) -> dict:
    try:
        resp = table.get_item(Key={"phone": phone})
        return resp.get("Item", {})
    except ClientError as e:
        logger.error("DynamoDB get_item error: %s", e)
        return {}


def save_session(phone: str, session: dict) -> None:
    session["phone"]      = phone
    session["updated_at"] = int(time.time())
    session["ttl"]        = int(time.time()) + SESSION_TTL_SECONDS
    try:
        table.put_item(Item=session)
    except ClientError as e:
        logger.error("DynamoDB put_item error: %s", e)


def clear_session(phone: str) -> None:
    try:
        table.delete_item(Key={"phone": phone})
    except ClientError as e:
        logger.error("DynamoDB delete_item error: %s", e)

# ---------------------------------------------------------------------------
# Bedrock / Claude
# ---------------------------------------------------------------------------

def call_claude(conversation_history: list) -> str:
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 512,
        "system": SYSTEM_PROMPT,
        "messages": conversation_history,
    }
    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"].strip()

# ---------------------------------------------------------------------------
# Notification helpers
# ---------------------------------------------------------------------------

def send_sms(to: str, body: str) -> None:
    twilio_cl.messages.create(to=to, from_=TWILIO_FROM_NUMBER, body=body)


def send_owner_summary_sms(data: dict, customer_phone: str) -> None:
    msg = (
        f"[CALL BOOKER] New booking request!\n"
        f"Name: {data['name']}\n"
        f"ZIP: {data['zip']}\n"
        f"Issue: {data['issue']}\n"
        f"Preferred time: {data['preferred_time']}\n"
        f"Customer #: {customer_phone}"
    )
    send_sms(OWNER_PHONE, msg)


def send_owner_email(data: dict, customer_phone: str) -> None:
    subject   = f"Call Booker – New Request from {data['name']}"
    body_text = (
        f"New booking request via SMS:\n\n"
        f"Name          : {data['name']}\n"
        f"ZIP           : {data['zip']}\n"
        f"Issue         : {data['issue']}\n"
        f"Preferred time: {data['preferred_time']}\n"
        f"Customer phone: {customer_phone}\n\n"
        f"Log in to your calendar to confirm the appointment."
    )
    try:
        ses.send_email(
            Source=SENDER_EMAIL,
            Destination={"ToAddresses": [OWNER_EMAIL]},
            Message={
                "Subject": {"Data": subject},
                "Body":    {"Text": {"Data": body_text}},
            },
        )
        logger.info("Owner summary email sent to %s", OWNER_EMAIL)
    except ClientError as e:
        logger.error("SES send_email error: %s", e)


def fire_completion_notifications(data: dict, customer_phone: str) -> None:
    """Owner summary SMS + customer Calendly SMS + SES email — all in parallel."""
    threads = [
        threading.Thread(target=send_owner_summary_sms, args=(data, customer_phone)),
        threading.Thread(
            target=send_sms,
            args=(customer_phone,
                  f"Thanks {data['name']}! Book your slot here: {CALENDLY_LINK}"),
        ),
        threading.Thread(target=send_owner_email, args=(data, customer_phone)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    # 1. Parse Twilio webhook (API Gateway passes body as URL-encoded string)
    raw_body = event.get("body", "") or ""
    if event.get("isBase64Encoded"):
        import base64
        raw_body = base64.b64decode(raw_body).decode("utf-8")

    params         = parse_qs(raw_body)
    customer_phone = params.get("From", ["unknown"])[0]
    inbound_text   = params.get("Body", [""])[0].strip()

    logger.info("Inbound SMS from %s: %s", customer_phone, inbound_text)

    # 2. Load or initialise session
    session = load_session(customer_phone)

    if not session:
        session = {
            "conversation_history": [],
            "collected": {},
            "complete": False,
            "created_at": int(time.time()),
        }

    # Already completed guard
    if session.get("complete"):
        twiml = MessagingResponse()
        twiml.message("You're already booked! Check your Calendly link. Reply RESTART to start over.")
        return _twiml_response(str(twiml))

    # RESTART keyword
    if inbound_text.upper() == "RESTART":
        clear_session(customer_phone)
        session = {
            "conversation_history": [],
            "collected": {},
            "complete": False,
            "created_at": int(time.time()),
        }

    # 3. Append customer message and call Claude
    history = session.get("conversation_history", [])
    history.append({"role": "user", "content": inbound_text})

    claude_reply = call_claude(history)
    logger.info("Claude reply: %s", claude_reply)

    # 4. Check if Claude returned a completion JSON
    reply_to_customer = claude_reply

    if claude_reply.lstrip().startswith("{"):
        try:
            parsed = json.loads(claude_reply)
            if parsed.get("complete"):
                collected = {
                    "name":           parsed["name"],
                    "zip":            parsed["zip"],
                    "issue":          parsed["issue"],
                    "preferred_time": parsed["preferred_time"],
                }
                reply_to_customer    = parsed.get("reply", "Got it! We'll be in touch soon.")
                session["collected"] = collected
                session["complete"]  = True
                fire_completion_notifications(collected, customer_phone)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Could not parse Claude JSON response: %s", e)

    # 5. Persist updated session
    history.append({"role": "assistant", "content": claude_reply})
    session["conversation_history"] = history
    save_session(customer_phone, session)

    # 6. Return TwiML
    twiml = MessagingResponse()
    twiml.message(reply_to_customer)
    return _twiml_response(str(twiml))


def _twiml_response(twiml_str: str) -> dict:
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/xml"},
        "body": twiml_str,
    }
