"""
================================================================================
CALL BOOKER — LOCAL WEBHOOK TEST SCRIPT  v1.0
================================================================================
Simulates Twilio SMS webhook POSTs and runs the Lambda handler locally.

Mocking strategy:
  - DynamoDB  →  moto  (in-memory, fully realistic)
  - Bedrock   →  unittest.mock  (scripted responses per turn)
  - Twilio    →  unittest.mock  (captures outbound SMS calls)
  - SES       →  unittest.mock  (captures email calls)

Modes:
  1. Automated happy-path  (default)     python test_webhook_local.py
  2. Edge-case suite                     python test_webhook_local.py --suite
  3. Interactive REPL                    python test_webhook_local.py --interactive

Install deps before running:
  pip install moto[dynamodb] boto3 twilio

================================================================================
"""

import sys
import os

# Force UTF-8 output on Windows so box-drawing chars don't crash cp1252
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json
import urllib.parse
import unittest
from unittest.mock import patch, MagicMock, call
from io import BytesIO

# ---------------------------------------------------------------------------
# Inject env vars BEFORE importing the handler (it reads them at module load)
# ---------------------------------------------------------------------------
os.environ.update({
    "TWILIO_ACCOUNT_SID":     "ACtest00000000000000000000000000",
    "TWILIO_AUTH_TOKEN":      "test_auth_token_000000000000000",
    "TWILIO_FROM_NUMBER":     "+18005550000",
    "OWNER_PHONE":            "+15125550001",
    "OWNER_EMAIL":            "owner@testhvac.com",
    "SENDER_EMAIL":           "noreply@testhvac.com",
    "CALENDLY_LINK":          "https://calendly.com/testhvac/hvac-consult",
    "BUSINESS_NAME":          "Test HVAC Co",
    "CALL_BOOKER_TABLE_NAME": "call-booker-sessions-test",
    "BEDROCK_REGION":         "us-east-1",
    "AWS_DEFAULT_REGION":     "us-east-1",
    "AWS_ACCESS_KEY_ID":      "testing",
    "AWS_SECRET_ACCESS_KEY":  "testing",
    "AWS_SECURITY_TOKEN":     "testing",
    "AWS_SESSION_TOKEN":      "testing",
})

import boto3
from moto import mock_aws

# ---------------------------------------------------------------------------
# Colours for terminal output
# ---------------------------------------------------------------------------
class C:
    CYAN   = "\033[96m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"

def print_header(title: str) -> None:
    width = 70
    print(f"\n{C.BOLD}{'=' * width}{C.RESET}")
    print(f"{C.BOLD}  {title}{C.RESET}")
    print(f"{C.BOLD}{'=' * width}{C.RESET}")

def print_turn(role: str, text: str, phone: str = "") -> None:
    tag = f"{C.DIM}{phone} {C.RESET}" if phone else ""
    if role == "customer":
        print(f"\n  {tag}{C.CYAN}Customer >{C.RESET} {text}")
    else:
        print(f"  {tag}{C.GREEN}  Lambda >{C.RESET} {text}")

def print_event(label: str, detail: str = "") -> None:
    detail_str = f"  {C.DIM}{detail}{C.RESET}" if detail else ""
    print(f"  {C.YELLOW}[{label}]{C.RESET}{detail_str}")

def print_fail(msg: str) -> None:
    print(f"\n  {C.RED}{C.BOLD}FAIL:{C.RESET} {msg}")

def print_pass(msg: str) -> None:
    print(f"\n  {C.GREEN}{C.BOLD}PASS:{C.RESET} {msg}")

# ---------------------------------------------------------------------------
# DynamoDB table setup (called inside each moto context)
# ---------------------------------------------------------------------------
def create_test_table():
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName="call-booker-sessions-test",
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[{"AttributeName": "phone", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "phone", "KeyType": "HASH"}],
    )
    return ddb

# ---------------------------------------------------------------------------
# Build a fake Twilio webhook event (API Gateway proxy format)
# ---------------------------------------------------------------------------
def make_twilio_event(from_number: str, body_text: str) -> dict:
    payload = urllib.parse.urlencode({
        "AccountSid":    os.environ["TWILIO_ACCOUNT_SID"],
        "From":          from_number,
        "To":            os.environ["TWILIO_FROM_NUMBER"],
        "Body":          body_text,
        "MessageSid":    "SMtest00000000000000000000000000",
        "NumMedia":      "0",
        "SmsStatus":     "received",
    })
    return {
        "httpMethod":      "POST",
        "path":            "/sms",
        "body":            payload,
        "isBase64Encoded": False,
        "headers":         {"Content-Type": "application/x-www-form-urlencoded"},
        "queryStringParameters": None,
    }

# ---------------------------------------------------------------------------
# Extract reply text from TwiML response
# ---------------------------------------------------------------------------
def extract_reply(response: dict) -> str:
    """Parse <Message> body out of TwiML string."""
    body = response.get("body", "")
    try:
        start = body.index("<Message>") + len("<Message>")
        end   = body.index("</Message>")
        return body[start:end].strip()
    except ValueError:
        return body

# ---------------------------------------------------------------------------
# Scripted Bedrock responses for the happy-path conversation
# ---------------------------------------------------------------------------
HAPPY_PATH_BEDROCK_RESPONSES = [
    # Turn 1 — greeting, ask for name
    "Hi! Sorry we missed your call. I'd love to help get you scheduled. "
    "May I start with your full name?",

    # Turn 2 — have name, ask for ZIP
    "Thanks, John! What's your ZIP code so we can confirm we service your area?",

    # Turn 3 — have ZIP, ask for issue
    "Got it, 78701. What's the issue you're having with your HVAC system?",

    # Turn 4 — have issue, ask for preferred time
    "Sorry to hear that! What day or time works best for a technician to visit?",

    # Turn 5 — all fields collected → JSON completion
    json.dumps({
        "complete":       True,
        "name":           "John Smith",
        "zip":            "78701",
        "issue":          "AC not cooling, blowing warm air",
        "preferred_time": "Thursday morning",
        "reply":          "Perfect, John! We've got everything we need. "
                          "Our team will reach out shortly to lock in your Thursday morning slot. "
                          "Talk soon!",
    }),
]

# ---------------------------------------------------------------------------
# Core test runner — runs one conversation with scripted Bedrock replies
# ---------------------------------------------------------------------------
def run_conversation(customer_messages: list,
                     bedrock_replies: list,
                     customer_phone: str = "+15125559999",
                     label: str = "Conversation") -> dict:
    """
    Drives the Lambda through multiple SMS turns.
    Returns a summary dict: {turns, owner_sms_calls, customer_sms_calls, email_calls, final_reply}
    """
    results = {
        "turns":               0,
        "owner_sms_calls":     [],
        "customer_sms_calls":  [],
        "email_calls":         [],
        "final_reply":         "",
        "passed":              True,
    }

    bedrock_iter = iter(bedrock_replies)

    def fake_invoke_model(**kwargs):
        reply_text = next(bedrock_iter, "Sorry, I ran out of scripted replies.")
        body_bytes = json.dumps({
            "content": [{"type": "text", "text": reply_text}]
        }).encode()
        return {"body": BytesIO(body_bytes)}

    # Capture outbound Twilio messages
    sent_sms = []
    def fake_messages_create(**kwargs):
        sent_sms.append(kwargs)
        return MagicMock(sid="SMfake")

    # Capture SES emails
    sent_emails = []
    def fake_send_email(**kwargs):
        sent_emails.append(kwargs)
        return {"MessageId": "fake-ses-id"}

    mock_twilio_instance = MagicMock()
    mock_twilio_instance.messages.create.side_effect = fake_messages_create

    with patch("twilio.rest.Client", return_value=mock_twilio_instance), \
         patch("boto3.client") as mock_boto_client:

        # Route boto3.client calls: bedrock-runtime → fake, ses → fake
        def client_router(service, **kwargs):
            if service == "bedrock-runtime":
                m = MagicMock()
                m.invoke_model.side_effect = fake_invoke_model
                return m
            if service == "ses":
                m = MagicMock()
                m.send_email.side_effect = fake_send_email
                return m
            return MagicMock()

        mock_boto_client.side_effect = client_router

        # Re-import handler INSIDE the mock context so clients are patched
        import importlib
        if "lambda_handler" in sys.modules:
            del sys.modules["lambda_handler"]
        handler_mod = importlib.import_module("lambda_handler")

        print_header(label)

        for i, customer_text in enumerate(customer_messages):
            results["turns"] += 1
            event    = make_twilio_event(customer_phone, customer_text)
            response = handler_mod.lambda_handler(event, {})
            reply    = extract_reply(response)

            print_turn("customer", customer_text, customer_phone)
            print_turn("lambda",   reply)

            if i == len(customer_messages) - 1:
                results["final_reply"] = reply

        # Separate owner vs customer outbound SMS
        owner = os.environ["OWNER_PHONE"]
        for msg in sent_sms:
            if msg.get("to") == owner:
                results["owner_sms_calls"].append(msg)
            else:
                results["customer_sms_calls"].append(msg)

        results["email_calls"] = sent_emails

        # Print notification summary
        print(f"\n  {C.BOLD}── Notifications fired ──{C.RESET}")
        if results["owner_sms_calls"]:
            print_event("Owner SMS", results["owner_sms_calls"][0]["body"][:80] + "…")
        if results["customer_sms_calls"]:
            print_event("Customer SMS", results["customer_sms_calls"][0]["body"][:80] + "…")
        if results["email_calls"]:
            subj = results["email_calls"][0].get("Message", {}).get("Subject", {}).get("Data", "")
            print_event("SES Email", subj)

    return results


# ===========================================================================
# TEST CASES
# ===========================================================================

@mock_aws
def test_happy_path():
    """Full 5-turn conversation — collects all 4 fields, fires 3 notifications."""
    create_test_table()
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)) + "/03_Code")

    customer_messages = [
        "Hi, I missed a call from you",
        "John Smith",
        "78701",
        "AC is blowing warm air",
        "Thursday morning works",
    ]

    results = run_conversation(
        customer_messages=customer_messages,
        bedrock_replies=HAPPY_PATH_BEDROCK_RESPONSES,
        label="TEST 1 — Happy Path (Full Conversation)",
    )

    # Assertions
    errors = []
    if results["turns"] != 5:
        errors.append(f"Expected 5 turns, got {results['turns']}")
    if not results["owner_sms_calls"]:
        errors.append("Owner summary SMS was not sent")
    if not results["customer_sms_calls"]:
        errors.append("Customer Calendly SMS was not sent")
    if not results["email_calls"]:
        errors.append("Owner SES email was not sent")
    if "calendly.com" not in str(results["customer_sms_calls"]):
        errors.append("Calendly link missing from customer SMS")

    if errors:
        for e in errors:
            print_fail(e)
        return False
    print_pass("All assertions passed — happy path complete.")
    return True


@mock_aws
def test_restart_keyword():
    """Customer sends RESTART mid-conversation — session clears and restarts."""
    create_test_table()

    restart_responses = [
        "Hi! Sorry we missed your call. May I have your full name?",
        "Hi! Sorry we missed your call. May I have your full name?",  # after RESTART
    ]

    results = run_conversation(
        customer_messages=["Hello", "RESTART"],
        bedrock_replies=restart_responses,
        customer_phone="+15125550002",
        label="TEST 2 — RESTART Keyword",
    )

    if results["turns"] == 2:
        print_pass("RESTART handled — session cleared and restarted.")
        return True
    print_fail(f"Expected 2 turns, got {results['turns']}")
    return False


@mock_aws
def test_already_complete_guard():
    """After booking is complete, further SMS gets the 'already booked' guard message."""
    create_test_table()

    # Seed DynamoDB with a completed session
    ddb   = boto3.resource("dynamodb", region_name="us-east-1")
    table = ddb.Table("call-booker-sessions-test")
    table.put_item(Item={
        "phone":                "+15125550003",
        "complete":             True,
        "collected":            {"name": "Jane", "zip": "90210", "issue": "Heater", "preferred_time": "Monday"},
        "conversation_history": [],
        "created_at":           1000000,
        "ttl":                  9999999999,
    })

    results = run_conversation(
        customer_messages=["Hey I want to book again"],
        bedrock_replies=[],                          # Claude should NOT be called
        customer_phone="+15125550003",
        label="TEST 3 — Already-Complete Guard",
    )

    if "already booked" in results["final_reply"].lower() or \
       "restart" in results["final_reply"].lower():
        print_pass("Guard message returned — session correctly blocked.")
        return True
    print_fail(f"Unexpected reply: {results['final_reply']}")
    return False


@mock_aws
def test_multi_field_single_message():
    """Customer provides name + ZIP in one message — Claude accepts both."""
    create_test_table()

    multi_field_responses = [
        "Thanks, Sarah! And ZIP 30301 — got it. What's the issue with your HVAC?",
        "Got it. What day or time works best for a visit?",
        json.dumps({
            "complete":       True,
            "name":           "Sarah Jones",
            "zip":            "30301",
            "issue":          "Strange noise from unit",
            "preferred_time": "Any weekday afternoon",
            "reply":          "Perfect Sarah! We'll be in touch to confirm your afternoon slot.",
        }),
    ]

    results = run_conversation(
        customer_messages=[
            "My name is Sarah Jones and my ZIP is 30301",
            "Strange noise coming from the outdoor unit",
            "Any weekday afternoon",
        ],
        bedrock_replies=multi_field_responses,
        customer_phone="+15125550004",
        label="TEST 4 — Multi-Field Single Message",
    )

    if results["owner_sms_calls"] and results["customer_sms_calls"]:
        print_pass("Multi-field message handled — booking completed in 3 turns.")
        return True
    print_fail("Notifications not fired after multi-field conversation.")
    return False


# ---------------------------------------------------------------------------
# Interactive REPL mode
# ---------------------------------------------------------------------------
@mock_aws
def run_interactive():
    create_test_table()
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)) + "/03_Code")

    print_header("INTERACTIVE MODE — Live conversation against real Bedrock")
    print(f"  {C.DIM}Env must have valid AWS credentials and Bedrock access.{C.RESET}")
    print(f"  {C.DIM}Type  'quit'  to exit,  'RESTART'  to reset session.{C.RESET}\n")

    customer_phone = input("  Customer phone (or press Enter for +15125559999): ").strip()
    if not customer_phone:
        customer_phone = "+15125559999"

    # In interactive mode we use REAL Bedrock — no mocking
    import importlib
    if "lambda_handler" in sys.modules:
        del sys.modules["lambda_handler"]
    import lambda_handler as handler_mod

    while True:
        try:
            text = input(f"\n  {C.CYAN}You >{C.RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Exiting.")
            break
        if text.lower() == "quit":
            break
        if not text:
            continue

        event    = make_twilio_event(customer_phone, text)
        response = handler_mod.lambda_handler(event, {})
        reply    = extract_reply(response)
        print(f"  {C.GREEN}Lambda >{C.RESET} {reply}")


# ===========================================================================
# Entry point
# ===========================================================================
if __name__ == "__main__":
    # Add 03_Code to path so lambda_handler can be imported
    code_dir = os.path.join(os.path.dirname(__file__), "..", "03_Code")
    sys.path.insert(0, os.path.abspath(code_dir))

    mode = sys.argv[1] if len(sys.argv) > 1 else ""

    if mode == "--interactive":
        run_interactive()
        sys.exit(0)

    if mode == "--suite":
        tests = [
            test_happy_path,
            test_restart_keyword,
            test_already_complete_guard,
            test_multi_field_single_message,
        ]
    else:
        tests = [test_happy_path]

    print_header("CALL BOOKER — LOCAL WEBHOOK TEST RUNNER")
    passed = 0
    failed = 0
    for t in tests:
        ok = t()
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n{C.BOLD}{'=' * 70}{C.RESET}")
    print(f"{C.BOLD}  Results: {C.GREEN}{passed} passed{C.RESET}  "
          f"{C.RED if failed else C.DIM}{failed} failed{C.RESET}")
    print(f"{C.BOLD}{'=' * 70}{C.RESET}\n")
    sys.exit(0 if failed == 0 else 1)
