# CALL BOOKER — Project Context for Claude

## Project Name
**Call Booker** — AI-powered missed call handler for HVAC businesses

## Purpose
When an HVAC customer calls and nobody answers, they get a text back automatically.
The AI (Claude via Bedrock) collects their name, ZIP, issue, and preferred appointment
time via SMS conversation, then fires a structured summary to the owner and a Calendly
booking link to the customer. No app, no portal — just SMS.

Target customer: small HVAC owner-operators (1–5 techs) who lose jobs to missed calls.
Business model: monthly SaaS fee per client ($97–$197/mo).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Inbound SMS | Twilio webhook → API Gateway |
| Compute | AWS Lambda (Python 3.12) |
| AI | Claude `claude-sonnet-4-20250514` via Amazon Bedrock |
| Session state | DynamoDB (TTL = 24h, PAY_PER_REQUEST) |
| Outbound SMS | Twilio REST API |
| Email fallback | AWS SES |
| Scheduling | EventBridge cron (daily 8am heartbeat) |
| Deploy | Serverless Framework v3 |
| Local testing | moto (DynamoDB mock) + unittest.mock (Bedrock/Twilio/SES) |

---

## Folder Structure

```
Project_1_Call_Booker_Master_Folder/
│
├── CLAUDE.md                          ← You are here. Project context for Claude Code.
├── CHANGELOG.md                       ← Version history, session-by-session changes
├── 01_Master_Build_Log.txt            ← Session log: what was done, what's next
├── .gitignore                         ← Excludes .env, .venv, __pycache__, *.zip
│
├── 02_Prompts/
│   ├── hvac-call-handler-prompt.txt   ← Claude system prompt (v1.0). Drives 4-field
│   │                                     SMS collection + JSON completion output.
│   ├── fallback-messages.txt          ← Placeholder: canned replies for edge cases
│   └── randomness-template.txt        ← Placeholder: prompt variation templates
│
├── 03_Code/
│   ├── lambda_handler.py              ← MAIN FUNCTION. Twilio webhook → DynamoDB
│   │                                     session → Bedrock → SMS reply. Fires owner
│   │                                     SMS + customer Calendly + SES email on completion.
│   ├── daily-heartbeat-function.py    ← HEARTBEAT FUNCTION. EventBridge cron at 8am.
│   │                                     Sends health-check SMS + 24h session stats to owner.
│   ├── serverless.yml                 ← Full IaC deploy config. Creates Lambda, API Gateway,
│   │                                     DynamoDB table, EventBridge rule, IAM role.
│   ├── .env.example                   ← All required env vars with descriptions. Copy to .env.
│   └── twilio-webhook-setup.txt       ← Placeholder: Twilio console step-by-step
│
├── 04_Onboarding/
│   ├── onboarding-checklist.txt       ← Placeholder: steps to onboard a new HVAC client
│   ├── pilot-outreach-message.txt     ← Placeholder: cold outreach script for first clients
│   └── pricing-sheet.txt             ← Placeholder: pricing tiers and offer structure
│
├── 05_Tests/
│   ├── test_webhook_local.py          ← LOCAL TEST RUNNER. 4 automated tests (happy path,
│   │                                     RESTART, already-complete guard, multi-field input).
│   │                                     Uses moto for DynamoDB, mocks Bedrock/Twilio/SES.
│   │                                     Run: PYTHONIOENCODING=utf-8 .venv/Scripts/python
│   │                                          05_Tests/test_webhook_local.py --suite
│   ├── fake-call-test-script.txt      ← Placeholder: manual SMS test scripts
│   └── test-results-log.txt          ← Placeholder: log of test runs and outcomes
│
├── 06_Docs/
│   ├── DEPLOYMENT_CHECKLIST.md        ← 11-step manual deploy guide. Covers IAM, Bedrock
│   │                                     model access, SES verification, DynamoDB, Twilio
│   │                                     webhook config, env vars, smoke test.
│   ├── Checklist_Summary.txt          ← Placeholder
│   └── Final_Decision_From_All_Research.txt  ← Placeholder
│
└── .venv/                             ← Local Python venv (not committed)
    └── (boto3, moto, twilio installed)
```

---

## MVP Scope

**In scope (MVP):**
- Inbound SMS triggers AI conversation
- Collect 4 fields: name, ZIP, HVAC issue, preferred time
- Owner receives structured SMS summary on completion
- Customer receives Calendly booking link on completion
- Owner receives SES email fallback (parallel, not sequential)
- Daily 8am health-check SMS to owner with 24h session stats
- RESTART keyword resets session
- Already-booked guard prevents duplicate sessions
- Multi-field single-message support (Claude handles gracefully)
- DynamoDB session state with 24h TTL auto-expiry
- Full local test suite (4 tests, no AWS account needed)

**Out of scope (post-MVP):**
- Voice call handling (IVR / TwiML Voice)
- Calendar API integration (Calendly link only for now)
- Multi-tenant dashboard
- Payment processing
- Follow-up reminder SMS
- Business hours logic
- CRM sync

---

## Environment Variables

All defined in `03_Code/.env.example`. Copy to `03_Code/.env` for local use.
Set as Lambda environment variables in console or via `serverless deploy`.

| Variable | Purpose |
|---|---|
| `TWILIO_ACCOUNT_SID` | Twilio account identifier |
| `TWILIO_AUTH_TOKEN` | Twilio API secret — rotate if exposed |
| `TWILIO_FROM_NUMBER` | Purchased Twilio SMS number e.g. `+18005551234` |
| `OWNER_PHONE` | Owner's cell — receives booking summary SMS |
| `OWNER_EMAIL` | Owner's email — receives SES fallback |
| `SENDER_EMAIL` | SES-verified sender address |
| `CALENDLY_LINK` | Full Calendly event URL sent to customer |
| `BUSINESS_NAME` | Used in SMS copy and email subjects |
| `CALL_BOOKER_TABLE_NAME` | DynamoDB table e.g. `call-booker-sessions-dev` |
| `BEDROCK_REGION` | AWS region with Bedrock access e.g. `us-east-1` |

**Never commit `.env` to git.** The `.gitignore` blocks it. In production, use
Lambda environment variables (encrypted at rest by AWS KMS).

---

## Deploy Commands

```bash
# One-time setup
cd Project_1_Call_Booker_Master_Folder
python -m venv .venv
.venv/Scripts/activate                         # Windows
pip install "moto[dynamodb]" boto3 twilio      # local test deps

# Local tests (no AWS needed)
PYTHONIOENCODING=utf-8 .venv/Scripts/python 05_Tests/test_webhook_local.py --suite

# Deploy to dev
cd 03_Code
serverless deploy --stage dev --aws-profile call-booker

# Deploy to prod
serverless deploy --stage prod --aws-profile call-booker

# Tail Lambda logs live
serverless logs -f smsWebhook --stage dev --tail

# Remove stack (tears down all AWS resources)
serverless remove --stage dev
```

---

## Build Status

### Complete
- [x] Project folder structure and session logging conventions
- [x] Claude system prompt (`hvac-call-handler-prompt.txt` v1.0)
  - 4-field collection, JSON completion output, edge cases, tone guide
- [x] Main Lambda function (`lambda_handler.py` v1.0)
  - Twilio webhook parsing, DynamoDB session state, Bedrock/Claude call,
    parallel notifications (owner SMS + customer Calendly SMS + SES email),
    RESTART keyword, already-complete guard
- [x] Daily heartbeat function (`daily-heartbeat-function.py` v1.0)
  - 8am EventBridge cron, DynamoDB 24h stats scan, health-check SMS to owner
- [x] Serverless deploy config (`serverless.yml`)
  - IAM role (Bedrock, SES, DynamoDB, SNS, CloudWatch), DynamoDB table,
    API Gateway, EventBridge rule, CloudWatch 5xx alarm, Stack Output for webhook URL
- [x] Environment variable template (`.env.example`)
- [x] `.gitignore`
- [x] Local test suite (`test_webhook_local.py`) — **4/4 tests passing**
  - Happy path, RESTART, already-complete guard, multi-field single message
- [x] Deployment checklist (`DEPLOYMENT_CHECKLIST.md`) — 11 steps, troubleshooting table

### Next
- [ ] Write `daily-heartbeat-function.py` — confirm file is complete (currently placeholder)
- [ ] Write `requirements.txt` for Lambda zip packaging
- [ ] Fill in placeholder files: `fallback-messages.txt`, `twilio-webhook-setup.txt`,
      `onboarding-checklist.txt`, `pilot-outreach-message.txt`, `pricing-sheet.txt`
- [ ] Run `serverless deploy --stage dev` and complete 06_Docs/DEPLOYMENT_CHECKLIST.md steps
- [ ] End-to-end smoke test with real Twilio number
- [ ] Onboard first pilot HVAC client

---

## Key Decisions & Notes

- **Model ID:** `us.anthropic.claude-sonnet-4-20250514-v1:0` — uses cross-region
  inference profile prefix (`us.`) which requires a wildcard in the Bedrock IAM policy.
- **Notifications are parallel:** `threading.Thread` fires owner SMS, customer SMS,
  and SES email simultaneously — keeps Lambda under Twilio's 15s response deadline.
- **No voice:** MVP is SMS-only. Twilio voice/TwiML is out of scope until paying clients validate the concept.
- **DynamoDB TTL:** Sessions auto-expire after 24h. No cleanup Lambda needed.
- **moto version:** Using moto v5 — decorator is `@mock_aws`, not `@mock_dynamodb` (removed in v4).
