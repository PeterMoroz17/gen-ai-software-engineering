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

This project was built with **Claude Code** as the primary development tool.

### How AI was used

**Scaffolding** - the full project structure (routes, model, validator, middleware) was generated from a single prompt describing the task requirements. Claude proposed the layered architecture (routes -> model -> validators) and the file layout.

**Fine-tuning** - once the scaffold was running, follow-up prompts iterated on specifics: adjusting route registration order so `/transactions/export` is not swallowed by `/:id`, refining the error response shape, and implementing multi-currency balance.

**Validation logic** - the ISO 4217 currency set (150+ codes) and all per-type account rules were generated by Claude and reviewed manually. The `hasAtMostTwoDecimals` helper was specifically discussed to avoid floating-point edge cases.

---