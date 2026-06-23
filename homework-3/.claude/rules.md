# Claude Code rules — Virtual Card Lifecycle & Spending Controls

These rules steer Claude (or any AI agent reading this directory) while working on this feature. They complement, and must not contradict, `../specification.md` and `../agents.md`.

## Naming
- Persisted fields and event payload keys: `snake_case` (`daily_limit_minor`, `card_id`, `idempotency_key`).
- Entity ids: UUIDv4, named `<entity>_id` (`card_id`, `transaction_id`, `audit_id`, `account_id`) — never raw `id`.
- Status enums are SCREAMING_SNAKE_CASE strings (`ACTIVE`, `USER_FROZEN`, `SYSTEM_FROZEN`, `CLOSED`) and must match the state machine in `specification.md` exactly — do not introduce a new status value without updating the spec first.

## Patterns to follow
- Money: always a `(integer_minor_units, currency_code)` pair. Never a bare number or float for an amount.
- Mutating actions: always take an `idempotency_key` parameter and always write an audit record in the same transaction as the state change.
- Reads on the authorization hot path (freeze state, remaining daily limit): always strongly consistent reads, never cache-backed.
- Errors: always one of the named codes in the spec's taxonomy; never a free-text-only error for a case the taxonomy already covers.
- Every management endpoint (`createCard`, `setFreezeState`, `setLimit`, `listTransactions`, `listAuditRecords`) goes through the rate-limit check (spec task 17) before any business-logic precondition — never add a new endpoint that skips it.

## What to avoid
- Never store, log, or echo back a full PAN or CVV. Use `masked_pan`/`card_id` only.
- Never let a cardholder-facing action transition a card out of `SYSTEM_FROZEN` — that's Ops/Compliance only (`liftSystemFreeze`).
- Never use offset-based pagination for transaction history — cursor-based only, per spec task 10.
- Never add a magic number for a platform constant (max cards, max limit, dedupe window, retention years, rate limits) — reference the named constants table in spec task 16.
- Never silently invent behavior for an edge case not listed in `specification.md`'s Edge Cases table — flag it instead.
- Never let a rate-limit rejection write an audit record or fire a notification — per spec task 17, no action was taken, so there's nothing to audit.

## FinTech-sensitive defaults
- Default to **fail closed**: when uncertain whether an authorization should be approved or declined, decline.
- Default to **audit everything**: if unsure whether an action needs an audit record, assume yes.
- Default to **least exposure**: when adding a new response/log/event field, ask "does this need to include this?" — if not clearly needed, leave it out.
- Default to **idempotent**: any new mutating endpoint/handler must be designed idempotent from the start, not retrofitted later.
