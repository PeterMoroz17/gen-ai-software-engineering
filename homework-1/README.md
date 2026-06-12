# Homework 1: Banking Transactions API

> **Student**: Peter Moroz
> **Submitted**: 2026-05-14
> **AI Tools Used**: Claude Code

---

## Overview

A REST API for managing banking transactions, built with Node.js and Express. All data is stored in memory. The API supports deposits, withdrawals, and transfers across multiple currencies, with full validation and filtering.

---

## Features Implemented

### Task 1 - Core API
All four required endpoints are implemented:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/transactions` | Create a transaction |
| `GET` | `/transactions` | List all transactions |
| `GET` | `/transactions/:id` | Get a transaction by ID |
| `GET` | `/accounts/:accountId/balance` | Get account balance |

### Task 2 - Validation
Every incoming transaction is validated before being stored:

- **Amount** - must be a positive number with at most 2 decimal places
- **Currency** - must be a valid ISO 4217 code (150+ currencies: USD, EUR, GBP, JPY, ...)
- **Type** - one of `deposit`, `withdrawal`, `transfer`
- **Account format** - must match `ACC-XXXXX` (5 alphanumeric characters)
- **Account presence** - `toAccount` required for deposits, `fromAccount` for withdrawals, both for transfers; source and destination cannot be the same account
- **Status** - optional; if provided must be `pending`, `completed`, or `failed`

Invalid requests return `400` with a structured error listing every failing field:
```json
{
  "error": "Validation failed",
  "details": [
    { "field": "amount", "message": "Amount must be a positive number" },
    { "field": "currency", "message": "Invalid currency code: XYZ" }
  ]
}
```

### Task 3 - Transaction Filtering
`GET /transactions` accepts any combination of query parameters:

| Parameter | Example | Description |
|-----------|---------|-------------|
| `accountId` | `ACC-12345` | Transactions where account is sender or receiver |
| `type` | `transfer` | Filter by transaction type |
| `from` | `2024-01-01` | Start of date range (inclusive) |
| `to` | `2024-12-31` | End of date range (inclusive, end of day) |

### Task 4 - Additional Features (all four implemented)

#### A - Transaction Summary
```
GET /accounts/:accountId/summary
```
Returns per-currency totals for deposits and withdrawals, transaction count, and most recent transaction date.

#### B - Interest Calculation
```
GET /accounts/:accountId/interest?rate=0.05&days=30&currency=USD
```
Calculates simple interest on the current balance for the given currency: `principal × rate × (days / 365)`. Returns principal, interest earned, and projected balance.

#### C - CSV Export
```
GET /transactions/export?format=csv
```
Streams all transactions as a downloadable CSV file with proper escaping.

#### D - Rate Limiting
100 requests per minute per IP address. Exceeding the limit returns `429 Too Many Requests` with a `Retry-After` header.

---

## Multi-Currency Design

Since the task specification does not define how balances should be handled across currencies, the API tracks each currency independently per account rather than collapsing everything into a single number. A `GET /balance` response looks like:

```json
{
  "accountId": "ACC-12345",
  "balances": {
    "USD": 749.50,
    "EUR": 500.00
  }
}
```

This means a USD transfer never affects a EUR balance, which reflects how real accounts work.

---

## Architecture

```
homework-1/
├── README.md
├── HOWTORUN.md
├── TASKS.md
├── package.json
├── .gitignore
├── src/
│   ├── index.js
│   ├── routes/
│   │   ├── transactions.js
│   │   └── accounts.js
│   ├── models/
│   │   └── transaction.js
│   ├── validators/
│   │   └── transactionValidator.js
│   └── middleware/
│       └── rateLimiter.js
├── demo/
│   ├── run.sh
│   ├── run.bat
│   ├── sample-requests.http
│   └── sample-data.json
└── docs/
    └── screenshots/
```


**Key decisions:**
- All business logic (balance calculation, filtering, aggregation) lives in the model layer, not in route handlers. Routes only parse input and format output.
- The rate limiter uses a plain `Map` - no Redis, no external package.
- CSV export is built without a csv library: values are quoted and internal `"` characters are doubled per RFC 4180.
- `GET /transactions/export` is registered before `GET /transactions/:id` in Express so it is not captured as an ID lookup.

---

## Tech Stack

| | |
|---|---|
| Runtime | Node.js v18+ |
| Framework | Express 4 |
| ID generation | uuid 11 |
| Storage | In-memory (plain array) |

---

## AI Usage

**Tool:** Claude Code (claude-sonnet-4-6)

### Prompts used

**Prompt 1 - Full implementation**
> "Right now we are working only with homework-1 folder. There you will find the task that needs to be completed in tasks.md. You have to implement them ALL. We will work on documentation in howtorun and readme later"

This single prompt, pointing at the spec file directly rather than re-describing requirements, generated the complete project: layered architecture (routes → model → validators → middleware), all four Task 4 options, 150+ ISO 4217 currency codes, and the multi-currency balance design.

**Prompt 2 - Documentation**
> "Good, now document how to run this program in howtorun.md"

Minor follow-up prompts fixed a PowerShell `-UseBasicParsing` warning in the examples and multiline command formatting in HOWTORUN.md.

### What was reviewed manually

- **Negative balance bug** - after testing, it was found that withdrawals and transfers could bring an account into negative funds. This was caught during manual testing and fixed.
- **Route registration order** - `/transactions/export` must be registered before `/:id` so Express does not treat `export` as a transaction ID. Claude flagged this; verified manually.
- **`hasAtMostTwoDecimals` logic** - reviewed to confirm it handles floating-point edge cases correctly (e.g. `0.1 + 0.2`).
- **Currency code list** - spot-checked a sample of the 150+ codes against the ISO 4217 standard.

### Observations

One sufficiently specific prompt produced a working implementation with no iteration needed on the core logic. The main limitation of this approach is that there is no visible prompt refinement process to document - the spec was handed directly to the model and the output was reviewed rather than iteratively prompted.

---