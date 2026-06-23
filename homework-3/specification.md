# Virtual Card Lifecycle & Spending Controls — Specification

> Ingest this file as the source of truth. Implement the Low-Level Tasks to satisfy the High-Level and Mid-Level Objectives. Treat every constraint in "Non-Functional & Policy" and "Implementation Notes" as binding, not advisory.

---

## High-Level Objective

Enable a cardholder to create, freeze/unfreeze, and set a daily spending limit on a virtual card, and to view its transaction history — while every state change is auditable, every authorization decision is enforced against a fresh limit/freeze state, and no party (including support staff) can observe the full card number.

**Scope boundary:** This spec covers only virtual card creation, freeze/unfreeze (user- and system-initiated), daily spending limit management, transaction history viewing, and the notifications triggered by these events. Physical cards, card replacement, dispute intake, multi-currency, and account/KYC onboarding are explicitly out of scope.

---

## Mid-Level Objectives

Each objective is observable — it describes a change in system state or user-visible outcome, not an implementation detail.

1. **M1 — Card Creation:** A cardholder with a funded, active account can request a virtual card and receive a usable card (masked PAN, expiry, CVV delivered once) within a bounded time, with the card immediately visible in their card list and an audit record created.
2. **M2 — Freeze / Unfreeze:** A cardholder can freeze or unfreeze their own card and see the state reflected immediately in their UI and in the authorization path (a frozen card declines all new authorizations). The Fraud/Velocity service can also freeze a card unilaterally (system freeze), and only Ops/Compliance — not the cardholder — can lift a system freeze.
3. **M3 — Spending Limit Management:** A cardholder can set or update a daily spending limit (in account currency, minor units) within platform-defined bounds, and that limit is enforced on the authorization path before the next eligible transaction is approved.
4. **M4 — Transaction History:** A cardholder can retrieve a paginated, chronological list of their card's transactions (approved, declined, reversed) with reasons for declines, reflecting writes within a bounded staleness window.
5. **M5 — Notifications:** The cardholder is notified (push/email — channel abstracted) when their card is created, when a transaction is declined for a limit or freeze reason, and when a system freeze is applied, within a bounded delay; notification failures do not block or roll back the underlying state change.

---

## Non-Functional & Policy

### Security & Data Handling
- Full PAN (card number) is **never** logged, returned in any API/error response, or stored outside the dedicated card-vault/tokenization boundary. All other surfaces (UI, logs, support tooling, audit trail) use a masked PAN (`first 6 + last 4`, e.g. `411111******1234`) and an internal `card_id` (not the PAN) as the join key.
- CVV is returned **exactly once**, at creation time, over an encrypted channel, and is never persisted in plaintext or logged at any layer.
- Support staff have read access to masked card data and transaction metadata only; they cannot view CVV, full PAN, or modify limits/freeze state — those actions are cardholder- or Ops/Compliance-initiated only.
- All monetary values are integers in minor currency units (e.g., cents); floating point is prohibited for money anywhere in the spec or its implementation.

### Audit & Logging
- Every state-changing action (create, freeze, unfreeze, limit change) produces an immutable audit record: actor (user/system/ops), actor id, timestamp (UTC, millisecond precision), action, before-state, after-state, and correlation/idempotency key.
- Audit records are retained for a minimum of 7 years (regulated card-data retention norm) and are write-once (no update/delete path in this spec's scope).
- System-initiated freezes additionally record the triggering signal/rule id from the Fraud/Velocity service for later compliance review.

### Reliability
- Card state (active/frozen) and limit reads on the authorization path must reflect the most recent successful write within **500 ms** (read-after-write staleness budget) — this is the bound that prevents a just-set limit or freeze from being bypassed by a near-simultaneous transaction.
- All state-changing endpoints are idempotent under client-supplied idempotency keys; retried requests with the same key return the original result without re-applying the action.

### Rate Limiting & Throttling (assumed targets — labeled as such)
- **Mutating actions per cardholder** (`createCard`, `setFreezeState`, `setLimit` combined): **10 requests/minute**, enforced per `account_id`. Rationale: this comfortably covers any legitimate human-driven sequence (e.g., freeze, check, unfreeze) while bounding rapid freeze/unfreeze cycling or repeated limit changes that would otherwise flood the audit log and the Notification Service with noise, and would otherwise be a cheap way to probe the authorization path's behavior.
- **`createCard` specifically**: additionally capped at **3 requests/minute** per account, independent of the combined mutating-action budget, since card creation is the most resource-costly action (it calls the card-vault/tokenization integration) and the rarest legitimate one.
- **`listTransactions` / `listAuditRecords` (read paths)**: **60 requests/minute** per caller — generous, since reads don't threaten state integrity, but still bounded to protect the 300ms read-latency budget under load.
- **Over-limit behavior**: requests beyond the budget are rejected with a dedicated `rate_limited` error (added to the error taxonomy below), not silently queued or dropped — the caller must see a distinguishable signal so legitimate retries can back off correctly.
- **Authorization-path protection**: the `evaluateAuthorization` check itself (task 8) is not rate-limited by this spec — it is invoked by the card network's own authorization flow, which has its own velocity controls upstream (the Fraud/Velocity Service). Rate limiting here applies to the cardholder-facing management APIs (create/freeze/limit/list), not to the authorization hot path, so the 50ms budget is unaffected by this section.

### Performance (assumed targets — labeled as such)
| Operation | Target | Rationale |
|---|---|---|
| Card creation (p99) | ≤ 2.0 s end-to-end | Card-issuance APIs (e.g., card-network tokenization round trips) typically run 500ms–1.5s; 2s keeps perceived UX "instant enough" for a one-time action. |
| Freeze/unfreeze write → authorization-path visibility (p99) | ≤ 500 ms | This is the safety-critical path: a fraud freeze must block spend almost immediately. |
| Limit update write → authorization-path visibility (p99) | ≤ 500 ms | Same rationale as freeze; prevents limit-bypass window. |
| Transaction list read (p95) | ≤ 300 ms for a page of 50 | Read-heavy, non-blocking path; generous budget vs. write paths. |
| Transaction list pagination | Cursor-based, max page size 100, default 25 | Avoids offset-pagination drift under concurrent writes; bounds payload size. |
| Notification delivery (p95, from trigger to dispatch) | ≤ 5 s | Notifications are best-effort and async; 5s is well inside user tolerance for a "you were declined" alert. |
| Authorization-path limit/freeze check itself | ≤ 50 ms (p99) | This sits inline in the card-network authorization response window (typically &lt;300ms total budget industry-wide); the check must be a small fraction of that. |
| Audit record write (same-transaction with the state change) | Included within each operation's end-to-end budget above, not additive | Per Implementation Notes, every state change writes its audit record in the same transaction; the audit write is therefore in the critical path of card creation, freeze/unfreeze, and limit updates and must be accounted for inside those budgets, not layered on top of them. |

All numbers above are **assumed targets for this exercise** — they are not measured from a real system — chosen to be directionally realistic for FinTech authorization-path UX and audit expectations, and are flagged as such rather than presented as verified SLAs.

---

## Implementation Notes (guardrails for builders / agents)

- **Money:** integer minor units + ISO 4217 currency code on every monetary field. This platform assumes **single-currency accounts** — every card inherits its account's currency at creation and that currency never changes. There is therefore no cross-currency conversion logic anywhere in this spec. `currency_mismatch` is **not** a multi-currency feature; it is a defensive check against a malformed/buggy request that supplies a `currency` field not matching the card's stored currency (e.g., a client bug sending `EUR` against a `USD` card). It should fire rarely, and its presence does not imply multi-currency support is in scope.
- **IDs:** All entities (`card_id`, `account_id`, `transaction_id`, `audit_id`) are UUIDv4 strings. The PAN itself is never used as or embedded in an ID.
- **Idempotency:** Every mutating action (`createCard`, `setFreezeState`, `setLimit`) requires a client-supplied `Idempotency-Key`; the same key + same actor + same payload must be a no-op on retry, returning the original result. A reused key with a *different* payload is a hard error (`409 idempotency_conflict`).
- **Error semantics:** Use a closed error-code taxonomy — `account_not_found`, `account_closed`, `card_limit_reached`, `card_not_found`, `card_frozen`, `invalid_limit_value`, `currency_mismatch`, `limit_exceeded`, `idempotency_conflict`, `stale_state`, `requires_compliance_review`, `rate_limited` — rather than free-text messages, so downstream systems (and the agent) can branch on them deterministically. Every error code used anywhere in this spec must appear in this list; every task below was checked against it.
- **State machine:** Card status is one of `ACTIVE`, `USER_FROZEN`, `SYSTEM_FROZEN`, `CLOSED`. The complete transition matrix is in "Card Status State Machine" below — do not implement any transition not listed there. `CLOSED` is reachable only as a hypothetical end-state for future work (e.g., a card-cancel action); **no action in this spec's scope ever transitions a card into `CLOSED`** — it exists in the enum solely so other checks (e.g., "is not `CLOSED`") are well-defined against a future state.
- **Ordering:** A user-initiated unfreeze must **never** succeed against a card whose current state is `SYSTEM_FROZEN`; that transition requires an Ops/Compliance actor. The agent must check current state inside the same transaction/lock as the write, not from a cached read.
- **Conventions:** snake_case for all field names in data/audit records; ISO 8601 UTC timestamps everywhere; no PII (name, email) inside audit `before-state`/`after-state` blobs — reference by id only.

### Card Status State Machine

| From ↓ / To → | `ACTIVE` | `USER_FROZEN` | `SYSTEM_FROZEN` | `CLOSED` |
|---|---|---|---|---|
| **`ACTIVE`** | — (no-op, idempotent) | ✅ cardholder, Ops/Compliance | ✅ System (Fraud/Velocity) | ❌ not reachable in this spec's scope |
| **`USER_FROZEN`** | ✅ cardholder, Ops/Compliance | — (no-op, idempotent) | ✅ System (Fraud/Velocity) | ❌ not reachable in this spec's scope |
| **`SYSTEM_FROZEN`** | ❌ cardholder forbidden (`requires_compliance_review`); ✅ Ops/Compliance only (`liftSystemFreeze`, task 6) | ❌ forbidden — only `ACTIVE` is a valid exit from `SYSTEM_FROZEN` | — (no-op, idempotent — task 5) | ❌ not reachable in this spec's scope |
| **`CLOSED`** | ❌ terminal | ❌ terminal | ❌ terminal | — (terminal, no-op) |

Any cell marked ❌ that is attempted must be rejected with a named error (`requires_compliance_review` for the cardholder-on-`SYSTEM_FROZEN` case; `card_not_found`-class handling is out of scope since no entry path to `CLOSED` exists yet) — never silently ignored or treated as success.

### Roles & Permissions

| Action | Cardholder | Support | Ops/Compliance | System (Fraud/Velocity) |
|---|---|---|---|---|
| `createCard` | ✅ (own account) | ❌ | ❌ | ❌ |
| `setFreezeState` (→ `USER_FROZEN` or → `ACTIVE` from `ACTIVE`/`USER_FROZEN`) | ✅ (own card) | ❌ | ✅ (operational override, e.g. on a support ticket) | ❌ |
| System freeze (→ `SYSTEM_FROZEN`) | ❌ | ❌ | ❌ | ✅ (via `velocity.threshold_exceeded` consumer) |
| `liftSystemFreeze` (`SYSTEM_FROZEN` → `ACTIVE`) | ❌ | ❌ | ✅ (requires `justification_text`) | ❌ |
| `setLimit` | ✅ (own card) | ❌ | ✅ (operational override) | ❌ |
| `listTransactions` (own card) | ✅ | ✅ (read-only, masked) | ✅ (read-only) | ❌ |
| `listAuditRecords` | ❌ | ❌ | ✅ | ❌ |
| View full PAN / CVV | ❌ (only at one-time creation delivery) | ❌ | ❌ | ❌ |

This table is the single source of truth for "who can call what" — Edge Cases and Low-Level Tasks reference it rather than restating permissions inline.

---

## Context

### Beginning context (hypothetical, for specificity)
- An existing **Account Service** exposing `getAccount(account_id)` → balance, currency, status (`ACTIVE`/`CLOSED`), with no virtual-card concept yet.
- An existing **Ledger Service** that records settled transactions but has no awareness of per-card limits or freeze state.
- An existing **Fraud/Velocity Service** that emits a `velocity.threshold_exceeded` event for an `account_id` + `card_id` but has no current consumer.
- An existing **Notification Service** with a generic `send(user_id, template, payload)` capability, currently unused by any card feature.
- No `Card Service`, `card` data store, or audit log for card actions exists yet.

### Ending context
- A new **Card Service** owning: `card` table/store (`card_id`, `account_id`, `masked_pan`, `expiry_month`, `expiry_year`, `vault_token`, `status`, `daily_limit_minor`, `currency`, `created_at`, `updated_at` — per task 1's schema), the card-vault integration for PAN/CVV (vaulted, not stored locally in plaintext), and the authorization-path limit/freeze/account-status check.
- A new **immutable audit log** (append-only store) for all card state changes, queryable by `card_id` and by date range, used by Ops/Compliance.
- A consumer wired from the Fraud/Velocity Service's `velocity.threshold_exceeded` event to the Card Service's system-freeze action.
- A consumer wired from card-state-change and decline events to the Notification Service.
- A read API for paginated transaction history per card, joining Ledger Service data with card decline records.
- This specification, `agents.md`, and editor/AI rules as the documented contract for any future implementation — no code is produced as part of this homework.

---

## Low-Level Tasks

Each task names the mid-level objective it serves and ends with acceptance criteria / definition of done.

### 1. Define card data model — *(M1)*
- Specify the `card` record: `card_id`, `account_id`, `masked_pan`, `expiry_month`, `expiry_year`, `vault_token` (opaque reference to vaulted PAN/CVV), `status`, `daily_limit_minor`, `currency`, `created_at`, `updated_at`. `expiry_month`/`expiry_year` are stored on the `card` record itself (not behind `vault_token`) because expiry is not a sensitive credential on its own — it's already exposed alongside the masked PAN in card-present-equivalent UI flows — whereas the full PAN and CVV remain vault-only.
- **Acceptance criteria:** schema reviewed against "no PAN at rest outside vault" rule; every field has a type and nullability stated; reviewer confirms no field can leak full PAN; `expiry_month`/`expiry_year` round-trip correctly through `createCard`'s output (task 2) so M1's "masked PAN, expiry, CVV delivered once" promise is actually satisfiable from this schema.

### 2. Specify `createCard` action contract — *(M1)*
- Inputs: `account_id`, `idempotency_key`, requested initial `daily_limit_minor` (optional, defaults to platform minimum).
- Preconditions: account exists and is `ACTIVE`; account does not already have more than the platform's max-cards-per-account (assumed: 5).
- Outputs: `card_id`, `masked_pan`, `expiry_month`, `expiry_year`, one-time CVV delivery reference, `status = ACTIVE`.
- **Acceptance criteria:** all precondition failures map to named error codes (`account_not_found`, `account_closed`, `card_limit_reached`); idempotent retry returns identical `card_id`.

### 3. Specify audit-record emission for card creation — *(M1, cross-cutting)*
- Define the exact audit payload for a `CARD_CREATED` event.
- **Acceptance criteria:** audit record contains actor, before-state (`none`), after-state (masked card summary), idempotency key, timestamp; reviewer confirms no PII beyond ids.

### 4. Specify `setFreezeState` (user-initiated) — *(M2)*
- Inputs: `card_id`, `requested_status ∈ {USER_FROZEN, ACTIVE}`, `idempotency_key`, `actor = cardholder`.
- Preconditions: caller owns the card; current status is not `SYSTEM_FROZEN` when requesting `ACTIVE` (must fail with `requires_compliance_review`); current status is not `CLOSED`.
- **Acceptance criteria:** implementation matches the Card Status State Machine table exactly (no transition implemented that isn't ✅ for the `cardholder` column there); state visible on authorization path within the 500ms budget — verified via the staleness test in Verification §2.

### 5. Specify system-initiated freeze consumer — *(M2)*
- Define the handler for `velocity.threshold_exceeded`: transitions card to `SYSTEM_FROZEN` regardless of current status (except `CLOSED`), records triggering rule id in audit.
- **Acceptance criteria:** handler is idempotent per event id; a card already `SYSTEM_FROZEN` re-receiving the event is a no-op; audit record includes the fraud rule id.

### 6. Specify Ops/Compliance override path — *(M2)*
- Define `liftSystemFreeze(card_id, ops_actor_id, justification_text, idempotency_key)`.
- **Acceptance criteria:** only succeeds from `SYSTEM_FROZEN` state; `justification_text` is mandatory and stored in the audit record; cardholder cannot call this action (authorization check documented).

### 7. Specify `setLimit` action contract — *(M3)*
- Inputs: `card_id`, `daily_limit_minor`, `currency` (must match card currency), `idempotency_key`.
- Preconditions: parent account exists and is `ACTIVE` (`account_not_found`/`account_closed` otherwise — same check as task 2, since a closed account should not be able to have its card's limit raised either); `platform_min_limit_minor ≤ daily_limit_minor ≤ platform_max_limit_minor`; card status is not `CLOSED`.
- **Acceptance criteria:** below-minimum, zero, negative, and over-max values all rejected with `invalid_limit_value`; account-closed requests rejected with `account_closed` (covers Edge Case #7's `setLimit` path directly, not only by cross-reference); currency mismatch rejected with `currency_mismatch`; successful update visible on authorization path within 500ms budget.

### 8. Specify authorization-path check — *(M2, M3 — shared enforcement point)*
- Define the single function the (hypothetical) authorization flow calls: `evaluateAuthorization(card_id, amount_minor, currency) -> {APPROVE | DECLINE(reason)}`.
- Logic order: card exists → parent account is `ACTIVE` (`account_closed` decline otherwise — a closed account must not be able to authorize spend through a still-`ACTIVE` card; this requires reading account status from the Account Service, not just card status, and is in scope precisely to close the gap Edge Case #7 would otherwise leave open) → card not `CLOSED`/frozen → currency matches → amount ≤ remaining daily limit (rolling UTC day) → APPROVE.
- **Acceptance criteria:** decline reasons map 1:1 to the error taxonomy (`account_closed`, `card_frozen`, `limit_exceeded`, `currency_mismatch`, `card_not_found`); function is read-only (no side effects) and documented as callable on the hot authorization path within the 50ms budget — the account-status check must also fit inside that budget via a strongly-consistent read (e.g., a synchronously-replicated account-status flag colocated with the Card Service's own data store), per `agents.md` Domain rule #5: authorization-path reads must never be served from a cache or an eventually-consistent replica, and the account-status check is no exception just because it crosses a service boundary.

### 9. Specify "remaining daily limit" computation — *(M3)*
- Define how spent-today is computed: sum of approved transaction amounts for the card where `transaction.created_at` falls within the current UTC calendar day, recomputed per check (no separate mutable counter to avoid drift).
- **Acceptance criteria:** spec states behavior at day rollover (resets to full limit at `00:00:00 UTC`); reviewer confirms no race condition between two concurrent authorizations both reading "remaining" before either writes (see Edge Cases #5).

### 10. Specify transaction history read model — *(M4)*
- Define `listTransactions(card_id, cursor, page_size ≤ 100, default 25)` returning transaction id, amount, currency, status (`APPROVED`/`DECLINED`/`REVERSED`), decline_reason (nullable), created_at, ordered newest-first.
- **Acceptance criteria:** cursor is opaque and based on `(created_at, transaction_id)` tuple, not offset; empty result set returns `[]` with a valid (non-null) cursor for "no more pages"; declined transactions include the same error-taxonomy reason as the authorization check.

### 11. Specify staleness/consistency note for transaction reads — *(M4)*
- Document that the read model may lag the ledger's write by up to the reliability budget; UI should not claim "real-time" stronger than that bound.
- **Acceptance criteria:** staleness bound stated in the same place as the API contract, not only in this spec's NFR section, so an implementer reading the task can't miss it.

### 12. Specify decline-notification trigger — *(M5)*
- On any `DECLINE(card_frozen)` or `DECLINE(limit_exceeded)` result from task 8, emit a notification event with masked card id, reason, amount.
- **Acceptance criteria:** notification payload contains no full PAN; notification failure is logged but does not retry-block the authorization response (already returned); duplicate suppression: at most one decline notification per card per reason per 5-minute window (avoid alert storms).

### 13. Specify card-created and freeze-event notification triggers — *(M5)*
- On `CARD_CREATED` and on a `SYSTEM_FROZEN` transition, emit a notification using the following template catalogue (named, not free-text, so the abstracted `send(user_id, template, payload)` call is deterministic):

  | Template id | Trigger | Payload fields |
  |---|---|---|
  | `card_created_v1` | Successful `createCard` | `card_id`, `masked_pan` |
  | `card_system_frozen_v1` | Transition to `SYSTEM_FROZEN` | `card_id`, `masked_pan`, support-contact action prompt (no fraud rule id) |
  | `transaction_declined_v1` | Decline per task 12 | `card_id`, `masked_pan`, `reason`, `amount_minor`, `currency` |

- **Acceptance criteria:** every notification trigger in this spec maps to exactly one template id above; `card_system_frozen_v1` explicitly tells the user to contact support (since they cannot self-unfreeze per the Roles & Permissions table); all template payloads reviewed against "no PAN, no internal rule ids" leakage rule.

### 14. Specify Ops/Compliance audit query capability — *(cross-cutting, M2/M3 verification support)*
- Define `listAuditRecords(card_id?, actor_type?, date_range)` for compliance review, read-only, no card-vault access.
- **Acceptance criteria:** query supports filtering by `actor_type = SYSTEM` to produce a "all auto-freezes this week" compliance report; result excludes any field not already defined as audit-safe in task 3.

### 15. Specify reconciliation check between Ledger and Card decline records — *(M4 verification support)*
- Define a periodic (assumed: hourly) batch check comparing Ledger-approved transaction sums per card against the authorization service's running "approved today" view.
- **Acceptance criteria:** mismatch beyond a defined tolerance (assumed: 0 minor units — exact match expected) raises a compliance alert, not a silent log line; this is the mechanism that would catch the race condition in Edge Cases #5 if it ever occurred in practice. Note: a mismatch discovered immediately after a write that is still inside the 500ms staleness budget (Reliability section) is expected and not an alert-worthy condition — the job's comparison window must exclude the trailing 500ms of its observation period to avoid false positives on data that simply hasn't propagated yet.

### 16. Specify the platform constants/config surface — *(cross-cutting)*
- Enumerate the assumed values used throughout (`max_cards_per_account = 5`, `platform_min_limit_minor` ≈ $10/day equivalent, `platform_max_limit_minor` ≈ $10,000/day equivalent, `decline_notification_dedupe_window = 5 min`, `audit_retention_years = 7`, `mutating_rate_limit = 10/min per account`, `create_card_rate_limit = 3/min per account`, `read_rate_limit = 60/min per caller`) as named, documented config rather than magic numbers scattered in tasks. `platform_min_limit_minor` is the default initial limit assigned by `createCard` (task 2) when the caller doesn't specify one, and is also the floor of task 7's `setLimit` precondition range (`platform_min_limit_minor ≤ daily_limit_minor ≤ platform_max_limit_minor`), so any value below it is rejected with `invalid_limit_value`.
- **Acceptance criteria:** a single table of constants exists and every task above references it by name rather than restating the literal value.

### 17. Specify rate limiting / throttling enforcement — *(cross-cutting, all of M1–M4)*
- Define a single throttling layer in front of `createCard`, `setFreezeState`, `setLimit`, `listTransactions`, and `listAuditRecords` that enforces the budgets named in Non-Functional & Policy → Rate Limiting (`mutating_rate_limit`, `create_card_rate_limit`, `read_rate_limit` from task 16's constants table), keyed by `account_id` for mutating actions and by caller identity for reads.
- Over-budget requests are rejected with `rate_limited` before any business-logic precondition is evaluated (i.e., a rate-limited `createCard` call never reaches the account-existence check) — this keeps the throttle cheap to evaluate and prevents it from leaking information about whether an account/card exists.
- **Acceptance criteria:** a documented test confirms the 11th mutating request within a rolling minute for one account is rejected with `rate_limited` while a 10th request from a *different* account in the same window succeeds (per-account isolation); a rejected request produces no audit record (since no action was taken) and no notification; the throttle check itself is excluded from the 50ms `evaluateAuthorization` budget per the Rate Limiting section's note that this applies to management APIs, not the authorization hot path.

---

## Edge Cases & Failure Modes

| # | Scenario | Expected behavior | Compliance/audit implication |
|---|---|---|---|
| 1 | Cardholder requests unfreeze on a `SYSTEM_FROZEN` card | Reject with `requires_compliance_review`; no state change | Audit record of the *attempt* (rejected action) retained for fraud pattern review |
| 2 | Two concurrent `setFreezeState` calls with different idempotency keys race on the same card | Last-writer-wins at the storage layer is **not acceptable**; the write must be done under a per-card lock/compare-and-swap on current status so the loser gets `stale_state` and must retry with fresh state | Both attempts audited; no silent lost update |
| 3 | `setLimit` called with a limit lower than today's already-spent amount | Accepted — new limit applies going forward; does not retroactively flag past approved transactions as invalid | Audit record shows old/new limit; no reversal triggered |
| 4 | Transaction attempted on a card mid-transition (freeze write in flight) | Authorization check must read the post-write state if the write has committed, or pre-write state if not — no partial/torn state; this is why task 8 must read inside the same transactional boundary as task 4/5 writes | If a transaction slips through during the staleness window, reconciliation (task 15) flags it |
| 5 | Two near-simultaneous authorizations both read "remaining limit" as sufficient, both approve, combined total exceeds limit | Documented as an accepted, bounded risk (classic TOCTOU on a hot path) mitigated by keeping the staleness budget tight (task 8/9) and caught after the fact by reconciliation (task 15) — not silently ignored | Flagged via reconciliation alert, reviewed by Ops/Compliance, not auto-reversed without manual review |
| 6 | `createCard` retried with same idempotency key but a different requested initial limit | Reject with `idempotency_conflict`; original card unaffected | Audit shows rejected conflicting attempt |
| 7 | Account is `CLOSED` after a card was created | Cardholder-initiated `setFreezeState`/`setLimit` requests are rejected with `account_closed`; existing card remains in its last-known status field (no automatic card status cascade — account closure cascading to card status is out of scope). However, per task 8, `evaluateAuthorization` independently checks account status on every authorization, so new spend is still blocked even though the card's own `status` field wasn't changed | Audit notes rejection reason for the cardholder action; authorization declines are visible via `listTransactions`/`listAuditRecords` |
| 8 | Pagination cursor from `listTransactions` is replayed after new transactions have landed | Returns the next page relative to the original cursor position (stable cursor semantics) — new transactions appear on a fresh first-page call, not retroactively inserted into an in-flight pagination sequence | N/A (read-only) |
| 9 | Notification Service is down when a decline notification should fire | Authorization response to the network is unaffected (already returned); notification is dropped/logged, not retried indefinitely (assumed: no notification durability guarantee in this scope) | Logged as a notification-delivery failure, not a compliance gap, since the audit record (not the notification) is the system of record |
| 10 | Support staff attempts to call `setLimit`, `setFreezeState`, `liftSystemFreeze`, or `listAuditRecords` | Rejected at the authorization-boundary level per the Roles & Permissions table (Support has no ❌-marked action) | Attempted-but-rejected action audited for security review |
| 11 | Empty transaction history for a newly created card | `listTransactions` returns `[]` with a valid terminating cursor, not an error | N/A |
| 12 | `daily_limit_minor` request of `0` | Rejected as `invalid_limit_value` — a card cannot be given a zero limit as a "soft freeze" substitute; freezing must use `setFreezeState` so the audit trail reflects intent correctly | Prevents ambiguous audit semantics between "frozen" and "zero-limit" |

---

## Verification

How each mid-level objective is confirmed met:

1. **M1 (Creation):** Unit-level documentation tests for precondition table (task 2); integration-style check (as documentation) that `CARD_CREATED` audit record (task 3) is produced for every successful creation and for zero failed ones; manual review checklist confirms masked-PAN-only exposure across API/log samples.
2. **M2 (Freeze/Unfreeze):** State-transition table (task 4) covered by one documented test case per row, including the two illegal transitions; concurrency check (Edge Case #2) documented as an integration-style test simulating two racing writes; staleness check measuring write→authorization-path visibility against the 500ms budget using synthetic timestamps.
3. **M3 (Limits):** Boundary tests for `daily_limit_minor` (0, negative, exactly at max, over max) per task 7; rollover-at-midnight-UTC test per task 9; the hourly reconciliation job (task 15) serves as an ongoing production-equivalent verification, not just a pre-release test.
4. **M4 (Transaction History):** Pagination correctness tests (empty set, single page, multi-page, cursor replay per Edge Case #8); staleness-bound spot-check comparing read-model lag to ledger writes.
5. **M5 (Notifications):** Dedupe-window test (two declines for the same reason within 5 minutes produce one notification); failure-isolation test confirming a simulated Notification Service outage does not affect the authorization response.

**Review checkpoints (manual compliance review, as documentation):**
- Pre-merge: data-handling reviewer confirms no task introduces a full-PAN-bearing field outside the vault boundary.
- Pre-release: Ops/Compliance reviews the audit-record schema (task 3) and the audit query capability (task 14) against the 7-year retention and write-once requirements.
- Post-release (recurring): weekly review of system-freeze audit records (via task 14 query) as a fraud-pattern sanity check.

**Data fixtures (as documentation):** a documented fixture set should include: one account with multiple cards, one card at exactly the daily limit boundary, one `SYSTEM_FROZEN` card, one card with a paginated 150+ transaction history, and one card with zero transactions — covering every edge case above without needing live data.

---

## Glossary
- **PAN** — Primary Account Number (the card number itself).
- **TOCTOU** — Time-of-check to time-of-use; the race class referenced in Edge Case #5.
- **Minor units** — smallest currency denomination (cents for USD), used to avoid floating-point money errors.
