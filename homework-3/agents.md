# agents.md — Virtual Card Lifecycle & Spending Controls

> Configuration for any AI coding agent (Claude Code, Copilot, Cursor, etc.) working on this feature. Read this together with `specification.md`, which is the source of truth for behavior. This file governs *how* the agent should work, not *what* the feature does.

## Tech stack assumptions

- Backend: a typed language with a real decimal/integer type for money (e.g., TypeScript with `bigint`/integer minor units, Java with `long` minor units, or Python with `int` — never `float`/`Decimal`-as-float-shim for money).
- Persistence: a transactional relational store for `card` and audit records (audit table must be append-only at the schema level — no `UPDATE`/`DELETE` grants on it, even for the application's own DB role).
- Card-vault/tokenization integration is a third-party or internal PCI-scoped boundary — the agent must never propose storing PAN/CVV in the application's own database, cache, logs, or message bus payloads.
- Async events (Fraud/Velocity signal, notifications) are assumed to flow through an at-least-once message bus; all consumers the agent writes must be idempotent per event id.

## Domain rules (banking-specific, non-negotiable)

1. **Money is always `(integer_minor_units, currency_code)`.** Never introduce a float for any monetary field, comparison, or arithmetic. Flag and refuse any instruction that would require float money math.
2. **Full PAN and CVV never leave the vault boundary.** Application code, logs, error messages, API responses, and message bus payloads carry only `card_id` and masked PAN. If a task seems to require the real PAN outside the vault, stop and flag it rather than implementing it.
3. **Every state-changing action is idempotent** under a caller-supplied idempotency key, and **every state-changing action writes an audit record** in the same logical transaction as the state change (not best-effort/fire-and-forget for the audit write itself).
4. **System-applied freezes can only be lifted by an Ops/Compliance actor.** Never implement a code path where a cardholder-facing endpoint can transition a card out of `SYSTEM_FROZEN`.
5. **Authorization-path reads (freeze state, remaining limit) must be done transactionally/with appropriate locking**, not from a cache or eventually-consistent replica, per `specification.md` task 8/9 and Edge Case #2/#5.
6. **Every cardholder-facing management endpoint (`createCard`, `setFreezeState`, `setLimit`, `listTransactions`, `listAuditRecords`) is rate-limited** per `specification.md`'s Rate Limiting & Throttling section and task 17. Never implement one of these endpoints without a throttle check ahead of its business logic, and never let the throttle check itself read from the same strongly-consistent path the authorization check uses — rate limiting protects the management APIs, not the `evaluateAuthorization` hot path.

## Code style & conventions

- snake_case for all persisted field names and audit payload keys; the language's native casing convention for in-code identifiers.
- ISO 8601 UTC timestamps everywhere; never local time or epoch-without-units in any field the agent introduces.
- Error handling uses the closed error-code taxonomy defined in `specification.md` (`limit_exceeded`, `card_frozen`, `card_not_found`, `invalid_limit_value`, `currency_mismatch`, `idempotency_conflict`, `stale_state`, `requires_compliance_review`, `account_not_found`, `account_closed`, `card_limit_reached`, `rate_limited`). Do not invent new ad hoc error strings — extend the taxonomy deliberately and update the spec if a genuinely new case is found.
- IDs are UUIDv4; never sequential integers for `card_id`/`transaction_id`/`audit_id` (avoids enumeration of card volume/activity).

## Testing & verification expectations

- For every low-level task implemented, write the corresponding test(s) named in `specification.md`'s "Verification" section before considering the task done — this is documentation-as-spec, but the expectation carries forward to real test files.
- Concurrency-sensitive logic (freeze/unfreeze, limit checks) requires a test that simulates the race explicitly (two concurrent writers / two concurrent authorization checks), not just a single-threaded happy-path test.
- Boundary values (limit = 0, limit = max, limit = max+1, empty transaction list, single-page vs multi-page pagination) are mandatory test cases, not optional.
- Any code touching the authorization path (`evaluateAuthorization`) must include a test asserting it performs no side effects (read-only), since it sits on the hot path described in the spec's performance table.

## Security & compliance constraints

- Never log a full PAN, even at debug level, even temporarily during development/debugging. Use masked PAN or `card_id` in all log statements.
- Never add a "support override" or "admin bypass" code path for freeze/limit actions that isn't explicitly defined in `specification.md` (task 6 is the only override path, and it requires `justification_text`).
- Treat the audit log as write-once: never generate code that updates or deletes an existing audit record, even for "fixing" a bad entry — corrections are new compensating records, never mutations.
- Any new field added to a request/response/event payload must be checked against the "no PAN, no CVV, minimal PII" rule before being added — when in doubt, exclude it and flag it for human review rather than including it speculatively.

## Handling edge cases (how the agent should behave when uncertain)

- If a requested change would violate a "non-negotiable" domain rule above, **do not implement it** — explain the conflict and propose the compliant alternative.
- If an edge case is encountered that is not listed in `specification.md`'s Edge Cases table, do not silently pick a behavior — surface it explicitly (e.g., as a comment/TODO referencing the missing case) so a human can extend the spec, rather than guessing silent behavior for a regulated financial flow.
- Prefer returning a named, documented error over a generic 500/exception for any failure mode already enumerated in the spec's error taxonomy.
- When in doubt between "fail closed" (decline/reject) and "fail open" (approve/allow), always fail closed for authorization-path decisions — this is a financial control surface, not a UX nicety.
