# CALL BOOKER — DEPLOYMENT CHECKLIST
**Version:** 1.0  
**Last Updated:** 2026-04-07  
**Estimated Time:** 45–90 minutes for a first-time deploy

Check off each item as you complete it. Steps are ordered to minimize backtracking.

---

## PRE-FLIGHT: ACCOUNTS & TOOLS

- [ ] AWS account created and billing alarm set (recommended: $10 threshold)
- [ ] AWS CLI installed — `aws --version`
- [ ] Serverless Framework installed — `npm install -g serverless`
- [ ] Python 3.12+ installed with working venv (see 05_Tests setup)
- [ ] Twilio account created at twilio.com (trial is fine for testing)
- [ ] Calendly account created and at least one event type published

---

## STEP 1 — AWS IAM: DEPLOY USER

> The IAM user is only for running `serverless deploy` from your machine.  
> Lambda itself uses an execution role created automatically by Serverless.

- [ ] Go to: **AWS Console → IAM → Users → Create User**
- [ ] Username: `call-booker-deploy`
- [ ] Attach policies directly — add these managed policies:
  - `AWSLambda_FullAccess`
  - `AmazonAPIGatewayAdministrator`
  - `AmazonDynamoDBFullAccess`
  - `AmazonS3FullAccess` *(Serverless uses S3 for deployment artifacts)*
  - `CloudWatchFullAccess`
  - `AmazonSESFullAccess`
  - `IAMFullAccess` *(required for Serverless to create the Lambda execution role)*
- [ ] Create user → go to **Security credentials** tab → **Create access key**
- [ ] Select "CLI" use case
- [ ] Download or copy **Access Key ID** and **Secret Access Key** — you will not see the secret again
- [ ] Run locally:
  ```bash
  aws configure --profile call-booker
  # paste Access Key ID, Secret Access Key, region (us-east-1), output format (json)
  ```
- [ ] Verify: `aws sts get-caller-identity --profile call-booker`

---

## STEP 2 — AWS BEDROCK: ENABLE MODEL ACCESS

> Bedrock models are off by default — you must request access before the Lambda can call them.

- [ ] Go to: **AWS Console → Amazon Bedrock → Model access** (left sidebar)
- [ ] Click **Manage model access**
- [ ] Find **Anthropic → Claude Sonnet** (`claude-sonnet-4-20250514`) — tick the checkbox
- [ ] Click **Save changes**
- [ ] Wait for status to change from "Available to request" → **Access granted** (usually instant, sometimes 1–2 min)
- [ ] Confirm region matches `BEDROCK_REGION` in your `.env` — model must be enabled in the same region

---

## STEP 3 — AWS SES: VERIFY EMAIL ADDRESSES

> SES starts in sandbox mode — you must verify both the sender and recipient email before any mail goes through.

- [ ] Go to: **AWS Console → Amazon SES → Verified identities → Create identity**
- [ ] **Verify sender email** (your `SENDER_EMAIL`):
  - Identity type: Email address
  - Enter: `noreply@yourbusiness.com` (or whatever you set as SENDER_EMAIL)
  - Click **Create identity** → check your inbox → click the verification link
  - Status must show **Verified** before continuing
- [ ] **Verify owner email** (your `OWNER_EMAIL`):
  - Repeat the same process for the owner's inbox
  - Status must show **Verified**
- [ ] *(Production only)* Request SES production access to send to unverified addresses:
  - SES Console → **Account dashboard** → **Request production access**
  - Approval takes 24–48 hours — do this early if you have a go-live deadline

---

## STEP 4 — AWS DYNAMODB: CREATE TABLE

> Serverless will create this automatically on `serverless deploy`.  
> Use this section only if you are creating it manually via console.

- [ ] Go to: **AWS Console → DynamoDB → Tables → Create table**
- [ ] Table name: `call-booker-sessions-dev` *(or `-prod` for production)*
- [ ] Partition key: `phone` — type: **String**
- [ ] Table settings: **Customize settings**
  - Capacity mode: **On-demand** (Pay per request — no capacity planning needed at MVP)
  - Table class: **DynamoDB Standard**
- [ ] Click **Create table**
- [ ] Once table is active → go to **Additional settings** tab → **Time to Live (TTL)**
  - TTL attribute name: `ttl`
  - Click **Enable**
- [ ] Note the table ARN — you may need it for manual IAM policy edits

---

## STEP 5 — TWILIO: PURCHASE PHONE NUMBER

- [ ] Log in to [console.twilio.com](https://console.twilio.com)
- [ ] Go to: **Phone Numbers → Manage → Buy a number**
- [ ] Search by area code (use owner's local area code for trust)
- [ ] Capabilities needed: **SMS** (voice optional)
- [ ] Click **Buy** — cost is ~$1.15/month
- [ ] Note the number — this is your `TWILIO_FROM_NUMBER` (e.g. `+15125550000`)
- [ ] Go to: **Account → Account info** — copy:
  - [ ] **Account SID** → `TWILIO_ACCOUNT_SID`
  - [ ] **Auth Token** (click to reveal) → `TWILIO_AUTH_TOKEN`

---

## STEP 6 — SERVERLESS DEPLOY

> Do this before configuring the Twilio webhook — you need the API Gateway URL first.

- [ ] Copy `.env.example` to `.env` and fill in all values:
  ```bash
  cp 03_Code/.env.example 03_Code/.env
  ```
- [ ] Activate your venv:
  ```bash
  .venv/Scripts/activate       # Windows
  source .venv/bin/activate    # Mac/Linux
  ```
- [ ] Install Python deps (first deploy only):
  ```bash
  pip install -r 03_Code/requirements.txt
  ```
- [ ] Deploy to dev:
  ```bash
  cd 03_Code
  serverless deploy --stage dev --aws-profile call-booker
  ```
- [ ] Wait for deploy to complete (~2–4 min first time)
- [ ] Copy the **Endpoint URL** printed at the end of deploy output:
  ```
  endpoints:
    POST - https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/dev/sms
  ```
  This is your `SmsWebhookUrl` — paste it into Twilio in the next step.
- [ ] Verify both functions appear in **AWS Console → Lambda → Functions**:
  - `call-booker-dev-smsWebhook`
  - `call-booker-dev-dailyHeartbeat`

---

## STEP 7 — TWILIO: CONFIGURE WEBHOOK

- [ ] Go to: **Twilio Console → Phone Numbers → Manage → Active numbers**
- [ ] Click your purchased number
- [ ] Scroll to **Messaging Configuration**
- [ ] Under **"A message comes in"**:
  - Type: **Webhook**
  - URL: paste your API Gateway endpoint from Step 6
    `https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/dev/sms`
  - Method: **HTTP POST**
- [ ] Click **Save configuration**
- [ ] **Send a test SMS** to your Twilio number from your personal phone
  - You should receive an automated reply within 3–5 seconds
  - If no reply in 10 s → check Lambda logs in CloudWatch

---

## STEP 8 — LAMBDA ENVIRONMENT VARIABLES (CONSOLE VERIFICATION)

> Serverless pulls these from your `.env` at deploy time.  
> Verify they landed correctly in the console.

- [ ] Go to: **AWS Console → Lambda → call-booker-dev-smsWebhook → Configuration → Environment variables**
- [ ] Confirm all 10 variables are present and correct:

  | Variable | Expected value |
  |---|---|
  | `TWILIO_ACCOUNT_SID` | `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
  | `TWILIO_AUTH_TOKEN` | 32-char hex string |
  | `TWILIO_FROM_NUMBER` | `+1XXXXXXXXXX` |
  | `OWNER_PHONE` | `+1XXXXXXXXXX` |
  | `OWNER_EMAIL` | owner's email address |
  | `SENDER_EMAIL` | SES-verified sender address |
  | `CALENDLY_LINK` | full Calendly URL |
  | `BUSINESS_NAME` | your business name |
  | `CALL_BOOKER_TABLE_NAME` | `call-booker-sessions-dev` |
  | `BEDROCK_REGION` | `us-east-1` |

- [ ] Repeat for `call-booker-dev-dailyHeartbeat`

---

## STEP 9 — EVENTBRIDGE: VERIFY HEARTBEAT SCHEDULE

- [ ] Go to: **AWS Console → EventBridge → Rules**
- [ ] Find: `call-booker-heartbeat-dev`
- [ ] Confirm schedule shows: `cron(0 14 * * ? *)` (or your adjusted UTC time)
- [ ] Click **Edit** → confirm target is `call-booker-dev-dailyHeartbeat`
- [ ] **Force a manual test run:**
  - Lambda Console → `call-booker-dev-dailyHeartbeat` → **Test** tab
  - Event JSON: `{}`
  - Click **Test** — you should receive a health-check SMS on `OWNER_PHONE` within 30 s

---

## STEP 10 — END-TO-END SMOKE TEST

- [ ] Text your Twilio number: `"Hi, I missed your call"`
- [ ] Verify you receive an SMS asking for your name
- [ ] Complete the full 4-field conversation
- [ ] Verify owner receives structured summary SMS
- [ ] Verify owner receives summary email
- [ ] Verify customer receives Calendly link SMS
- [ ] Check **DynamoDB → call-booker-sessions-dev** — confirm session record exists with `complete: true`
- [ ] Check **CloudWatch → Log groups → /aws/lambda/call-booker-dev-smsWebhook** — no errors

---

## STEP 11 — PRODUCTION DEPLOY (WHEN READY)

- [ ] Update `.env` with production values (real owner number, production Calendly link, etc.)
- [ ] Deploy to prod:
  ```bash
  serverless deploy --stage prod --aws-profile call-booker
  ```
- [ ] Create separate DynamoDB table: `call-booker-sessions-prod`
- [ ] Update Twilio webhook URL to prod API Gateway endpoint
- [ ] Request SES production access if not already done (Step 3)
- [ ] Set up CloudWatch alarm notifications (SNS → your email for 5xx alerts)
- [ ] Enable DynamoDB Point-in-Time Recovery:
  - DynamoDB Console → table → **Backups** → Enable PITR

---

## QUICK REFERENCE: KEY URLS

| Resource | Where to find it |
|---|---|
| Lambda functions | console.aws.amazon.com → Lambda |
| DynamoDB table | console.aws.amazon.com → DynamoDB → Tables |
| CloudWatch logs | console.aws.amazon.com → CloudWatch → Log groups |
| SES verified identities | console.aws.amazon.com → SES → Verified identities |
| Bedrock model access | console.aws.amazon.com → Bedrock → Model access |
| EventBridge rules | console.aws.amazon.com → EventBridge → Rules |
| Twilio console | console.twilio.com |

---

## TROUBLESHOOTING

| Symptom | Likely cause | Fix |
|---|---|---|
| No SMS reply from Lambda | Webhook URL wrong in Twilio | Re-paste API Gateway URL, ensure POST method |
| `AccessDeniedException` in logs | Bedrock model access not granted | Step 2 — enable model in correct region |
| `MessageRejected` SES error | Email address not verified | Step 3 — verify both sender and recipient |
| `ResourceNotFoundException` DynamoDB | Table name mismatch | Check `CALL_BOOKER_TABLE_NAME` env var matches actual table name |
| Lambda timeout | Bedrock cold start | Increase Lambda timeout to 29s in serverless.yml — already set |
| Twilio `11200` error | Lambda returned non-TwiML or 5xx | Check CloudWatch logs for Python exception |
