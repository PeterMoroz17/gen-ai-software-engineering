# How to Run Banking Transactions API

## Prerequisites

- [Node.js](https://nodejs.org/) v18 or higher
- npm (bundled with Node.js)

Verify your versions:
```bash
node --version
npm --version
```

---

## Quick Start

### 1. Install dependencies

```bash
cd homework-1
npm install
```

### 2. Start the server

```bash
npm start
```

The API will be available at `http://localhost:3000`.

To change the port, set the `PORT` environment variable:

```bash
PORT=8080 npm start        # macOS / Linux
$env:PORT=8080; npm start  # Windows PowerShell
```

### 3. (Optional) Development mode with auto-reload

```bash
npm run dev
```

---

## Testing the API

### Option A — VS Code REST Client

1. Install the [REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) extension.
2. Open [demo/sample-requests.http](demo/sample-requests.http).
3. Click **Send Request** above any request block.

### Option B — PowerShell (Invoke-RestMethod)

PowerShell's built-in `Invoke-RestMethod` avoids all curl quoting issues. Use single quotes around the JSON body — no escaping needed.

```powershell
# Create a deposit
Invoke-RestMethod -Uri http://localhost:3000/transactions -Method POST -ContentType "application/json" -Body '{"toAccount":"ACC-12345","amount":1000,"currency":"USD","type":"deposit"}'

# Create a transfer
Invoke-RestMethod -Uri http://localhost:3000/transactions -Method POST -ContentType "application/json" -Body '{"fromAccount":"ACC-12345","toAccount":"ACC-67890","amount":250.50,"currency":"USD","type":"transfer"}'

# Create a withdrawal
Invoke-RestMethod -Uri http://localhost:3000/transactions -Method POST -ContentType "application/json" -Body '{"fromAccount":"ACC-67890","amount":100,"currency":"USD","type":"withdrawal"}'

# List all transactions
Invoke-RestMethod -Uri http://localhost:3000/transactions

# Filter by account
Invoke-RestMethod -Uri "http://localhost:3000/transactions?accountId=ACC-12345"

# Filter by type and date range
Invoke-RestMethod -Uri "http://localhost:3000/transactions?type=transfer&from=2024-01-01&to=2026-12-31"

# Get a specific transaction (replace <id> with a real UUID from a previous response)
Invoke-RestMethod -Uri http://localhost:3000/transactions/<id>

# Get account balance
Invoke-RestMethod -Uri http://localhost:3000/accounts/ACC-12345/balance

# Get account summary
Invoke-RestMethod -Uri http://localhost:3000/accounts/ACC-12345/summary

# Calculate simple interest (5% annual rate, 30 days)
Invoke-RestMethod -Uri "http://localhost:3000/accounts/ACC-12345/interest?rate=0.05&days=30"

# Export all transactions as CSV
Invoke-WebRequest -Uri "http://localhost:3000/transactions/export?format=csv" -OutFile "transactions.csv" -UseBasicParsing
```

### Option C — Demo scripts

```bash
# macOS / Linux
bash demo/run.sh

# Windows
demo\run.bat
```

---

## API Endpoints Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/transactions` | Create a transaction |
| `GET` | `/transactions` | List transactions (filterable) |
| `GET` | `/transactions/:id` | Get transaction by ID |
| `GET` | `/transactions/export?format=csv` | Export all as CSV |
| `GET` | `/accounts/:accountId/balance` | Get account balance |
| `GET` | `/accounts/:accountId/summary` | Deposits, withdrawals, count |
| `GET` | `/accounts/:accountId/interest?rate=&days=` | Simple interest projection |

### Query parameters for `GET /transactions`

| Parameter | Example | Description |
|-----------|---------|-------------|
| `accountId` | `ACC-12345` | Filter by sender or receiver |
| `type` | `transfer` | `deposit`, `withdrawal`, or `transfer` |
| `from` | `2024-01-01` | Start date (inclusive) |
| `to` | `2024-12-31` | End date (inclusive, end of day) |

---

## Notes

- Storage is **in-memory** — all data is lost when the server restarts.
- Account IDs must match the format `ACC-XXXXX` (5 alphanumeric characters, e.g. `ACC-12345`, `ACC-AB1CD`).
- Currency codes must be valid [ISO 4217](https://en.wikipedia.org/wiki/ISO_4217) codes (e.g. `USD`, `EUR`, `GBP`).
- The rate limiter allows **100 requests per minute per IP**; exceeding it returns `429 Too Many Requests`.
