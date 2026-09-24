# Automated expense audit PoC

Receipt extraction → deterministic policy evaluation → optional manager notification.
The IMAP listener, manager decision handler, and ERP integration are **not implemented yet**.
No audit status authorizes payment. `APPROVED` currently means policy checks passed.

## Run locally

Python 3.11+:

```sh
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
venv/bin/python -B -m unittest discover -s tests -v
venv/bin/python -B main.py --demo
```

Demo mode requires no API key, performs no OCR, and sends no email by default.
The sample requests $215, with $180 compliant and the $35 meal flagged for alcohol.

To inspect a local test notification:

```sh
docker compose up -d mailpit
venv/bin/python -B main.py --demo --send-email
```

Open http://localhost:8025. SMTP is bound to localhost:1025. The current SMTP
implementation is for a local capture server; Gmail authentication/TLS is not implemented.
The Compose service has not been integration-tested in this change.

For real OCR, configure `OPENAI_API_KEY` in `.env` and run:

```sh
venv/bin/python -B main.py --receipt tests/sample_receipt.png \
  --employee-email employee@example.org --employee-name 'Example Employee' \
  --purpose 'Conference'
```

PNG, JPEG, and WebP are accepted. PDFs fail explicitly pending a PDF input adapter.
OCR errors/refusals stop processing. Missing credentials never substitute fabricated data.
API parsing follows the [official Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs).
Live OCR and SMTP were not exercised by the offline test suite.

## Policy semantics and remaining boundaries

- Money is nonnegative, finite `Decimal`, with at most two decimal places. JSON serializes money as strings.
- Meals are whole meal purchases, including tax/tip and alcohol, not individual menu lines.
  The $40 cap applies per meal; the $80 cap applies per actual date within a submission.
  Missing meal dates are flagged. Trip length cannot offset an over-cap day.
- Lodging amounts represent a single night. OCR is instructed to extract actual nightly
  charges, never average a stay. If these are unavailable it retains the whole total;
  totals over $200 are conservatively flagged. A dedicated nightly breakdown schema and
  reconciliation still need to be added before reliable multi-night hotel processing.
- Courses are grouped by year and include trusted prior spending passed to
  `evaluate_report(report, course_spend_by_year={2026: Decimal('500.00')})`.
  Missing history is flagged; the CLI does not yet load a ledger. History must exclude
  the current submission. Explicit zero means verified no previous spending.
- Receipts are required strictly **above** $10, matching the existing rule.
- Every item in an over-cap daily/annual group is withheld, rather than partially reimbursed.
  This preserves the original all-or-nothing item policy; confirm it with the policy owner.
- Non-USD/unknown currency is flagged. Existing programmatic callers default to USD for
  compatibility; OCR is instructed to extract the currency or return UNKNOWN.
- These checks validate extracted facts, not their truth. Misread amounts, dates,
  categories, alcohol indicators, duplicate receipts, and cross-submission meal totals
  still require reconciliation, a ledger, and human review.

## Next milestones, in implementation order

1. **Persistent submission and spending ledger.** Add SQLite for the PoC, with immutable
   receipt hashes, employee IDs, policy version, original extraction, audit JSON,
   assigned manager ID, and timestamps. Use separate states: received, extracted,
   audited, awaiting decision, decided, payment pending, payment acknowledged.
   Read daily/annual prior spend from this ledger and account for pending approvals
   transactionally so concurrent submissions cannot bypass caps.
   Acceptance: restart recovery and duplicate/concurrent submission tests.

2. **IMAP ingestion.** Use a dedicated TLS mailbox and environment-based credentials.
   Fetch unseen messages using UID and BODY.PEEK; persist `(mailbox, UIDVALIDITY, UID)`
   before processing and mark seen only after durable acceptance. Process attachments
   from bytes with size/count limits and verified media types. Store failures for retry
   or manual review. Associate employees with a trusted directory; a From header alone
   is not proof of identity. Add PDF rendering/input support and total reconciliation.
   Acceptance: MIME fixtures covering multiple attachments, unsupported types, retries,
   and repeated delivery. Mailpit remains an outbound capture tool in this setup.

3. **Manager decisions.** Correlate each notification and reply to a persisted report ID
   and assigned manager. Use authenticated identity or a signed, expiring approval link;
   matching a spoofable From header is insufficient. Parse only the new reply text with
   exact commands: APPROVE COMPLIANT, REJECT, APPROVE ALL. Require a nonempty override
   reason for APPROVE ALL. Persist manager_id, UTC timestamp, decision, override_reason,
   and resulting amount in one transaction. Never interpret quoted previous messages
   as a decision. Conflicting or duplicate decisions cannot change a finalized record.
   Acceptance: unauthorized, ambiguous, missing-reason, replay, and concurrent reply tests.

4. **Mock ERP endpoint and transactional outbox.** In the decision transaction create
   an outbox event containing report_id, decision_id, employee_id, manager_id,
   decided_at, policy_version, currency, approved_amount, and override_reason.
   REJECT records a decision but produces no payment instruction. Send approved events
   to a local mock HTTP endpoint with an idempotency key based on decision_id. Retry
   timeouts with backoff; mark acknowledged only after success. The receiver deduplicates
   retries, including when it accepted a request but the response was lost.
   Acceptance: one recorded mock payment after retries/restarts and no payment on rejection.

Before a real-mailbox pilot, complete these acceptance checks with synthetic receipts,
including actual nightly hotel breakdowns and meal totals split across submissions.

## Repository housekeeping

`.gitignore` excludes environments, secrets, databases, and future bytecode. The existing
repository already tracks several `__pycache__` files; remove those from the Git index
in a follow-up cleanup (ignore rules do not untrack existing files).
