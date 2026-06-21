# API_REFERENCE.md

# Customer Support Ticket Management API Reference

A REST API for managing customer support tickets.

**Base URL:** Application root (no versioning)
**Authentication:** None
**Persistence:** In-memory only (data resets on restart)

---

# Overview

This API provides:

* Ticket CRUD operations
* Bulk import (CSV / JSON / XML)
* Keyword-based auto-classification
* Filtering via query parameters

When `auto_classify=true` is used, the system populates:

* `category`
* `priority`
* `classification_confidence`
* `classification_reasoning`

---

# Data Models

---

## Enums

### Category

* account_access
* technical_issue
* billing_question
* feature_request
* bug_report
* other

### Priority

* urgent
* high
* medium
* low

### Status

* new
* in_progress
* waiting_customer
* resolved
* closed

### Source

* web_form
* email
* api
* chat
* phone

### DeviceType

* desktop
* mobile
* tablet

---

## Metadata

| Field       | Type       | Required | Notes          |
| ----------- | ---------- | -------- | -------------- |
| source      | Source     | No       | Default: `api` |
| browser     | string     | No       | Optional       |
| device_type | DeviceType | No       | Optional       |

---

## TicketCreate

Used for `POST /tickets` and import records.

| Field          | Type         | Required | Constraints       |
| -------------- | ------------ | -------- | ----------------- |
| customer_id    | string       | Yes      | must not be blank |
| customer_email | string       | Yes      | valid email       |
| customer_name  | string       | Yes      | must not be blank |
| subject        | string       | Yes      | 1–200 chars       |
| description    | string       | Yes      | 10–2000 chars     |
| category       | Category     | No       | optional          |
| priority       | Priority     | No       | optional          |
| status         | Status       | No       | default: `new`    |
| assigned_to    | string       | No       | optional          |
| tags           | list[string] | No       | default: []       |
| metadata       | Metadata     | No       | default object    |

---

## TicketUpdate (CORRECTED)

Used for `PUT /tickets/{id}`.

⚠ All fields optional. Only provided fields are updated.

| Field          | Type                   |
| -------------- | ---------------------- |
| customer_email | string (email)         |
| customer_name  | string                 |
| subject        | string (1–200 chars)   |
| description    | string (10–2000 chars) |
| category       | Category               |
| priority       | Priority               |
| status         | Status                 |
| assigned_to    | string                 |
| tags           | list[string]           |
| metadata       | Metadata               |

❌ `customer_id` is NOT editable via update.

---

## Ticket

Extends `TicketCreate`.

| Field                     | Type            | Notes                                         |
| ------------------------- | --------------- | --------------------------------------------- |
| id                        | string          | UUID4                                         |
| created_at                | datetime        | UTC                                           |
| updated_at                | datetime        | updated on change                             |
| resolved_at               | datetime | null | set once when status first becomes `resolved` |
| classification_confidence | float | null    | auto-classification                           |
| classification_reasoning  | string | null   | classifier output                             |

---

## ImportSummary

| Field      | Type       |
| ---------- | ---------- |
| total      | int        |
| successful | int        |
| failed     | int        |
| errors     | list[dict] |

Error object:

```json
{
  "index": 0,
  "record": {},
  "error": "string or validation error object"
}
```

---

## ClassificationResult

Returned by:

`POST /tickets/{id}/auto-classify`

| Field          | Type         |
| -------------- | ------------ |
| category       | Category     |
| priority       | Priority     |
| confidence     | float        |
| reasoning      | string       |
| keywords_found | list[string] |

---

# Classification Behavior (IMPORTANT)

Classification is deterministic and keyword-based.

## Category reasoning format

If matches exist:

```
Matched category '<category>' keywords: [<list of matched keywords>]
```

If no matches:

```
No category keywords matched; defaulting to 'other'
```

---

## Priority reasoning format

If matches exist:

```
Matched priority '<priority>' keywords: [<list of matched keywords>]
```

If no matches:

```
No priority keywords matched; defaulting to 'medium'
```

---

## Confidence calculation

* Compute keyword hit ratio per category
* Best score = matched_keywords / total_keywords
* Confidence = `min(best_score * 5, 1.0)`
* If no category matches → confidence = `0.0`

---

# Endpoints

---

## POST /tickets

Create a ticket.

### Query Params

| Name          | Type | Default |
| ------------- | ---- | ------- |
| auto_classify | bool | false   |

---

### Request

```json
{
  "customer_id": "CUST-1001",
  "customer_email": "user@example.com",
  "customer_name": "John Doe",
  "subject": "Cannot access account",
  "description": "I cannot access my account after resetting my password and need assistance.",
  "status": "new",
  "tags": ["login"],
  "metadata": {
    "source": "web_form",
    "browser": "Chrome",
    "device_type": "desktop"
  }
}
```

---

### Response (201)

```json
{
  "customer_id": "CUST-1001",
  "customer_email": "user@example.com",
  "customer_name": "John Doe",
  "subject": "Cannot access account",
  "description": "I cannot access my account after resetting my password and need assistance.",
  "category": "account_access",
  "priority": "urgent",
  "status": "new",
  "assigned_to": null,
  "tags": ["login"],
  "metadata": {
    "source": "web_form",
    "browser": "Chrome",
    "device_type": "desktop"
  },
  "id": "uuid",
  "created_at": "2026-06-18T12:00:00Z",
  "updated_at": "2026-06-18T12:00:00Z",
  "resolved_at": null,
  "classification_confidence": 0.43,
  "classification_reasoning": "Matched category 'account_access' keywords: ['password', 'reset']. Matched priority 'urgent' keywords: ['cannot access']"
}
```

---

### cURL

```bash
curl -X POST "http://localhost:8000/tickets?auto_classify=true" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id":"CUST-1001",
    "customer_email":"user@example.com",
    "customer_name":"John Doe",
    "subject":"Cannot access account",
    "description":"I cannot access my account after resetting my password and need assistance."
  }'
```

---

## POST /tickets/import

Bulk import tickets.

### Request

```bash
curl -X POST "http://localhost:8000/tickets/import?auto_classify=true" \
  -F "file=@sample_tickets.csv"
```

---

### Response (200)

```json
{
  "total": 3,
  "successful": 2,
  "failed": 1,
  "errors": [
    {
      "index": 1,
      "record": {},
      "error": "Validation error"
    }
  ]
}
```

---

## GET /tickets

List tickets (AND filtering).

### Query Params

| Name     | Type     |
| -------- | -------- |
| category | Category |
| priority | Priority |
| status   | Status   |

---

### Example

```
GET /tickets?category=technical_issue&priority=high
```

---

### Response (200)

```json
[
  {
    "customer_id": "CUST-2001",
    "customer_email": "a@b.com",
    "customer_name": "Alice",
    "subject": "App crash",
    "description": "App crashes on startup",
    "category": "technical_issue",
    "priority": "high",
    "status": "in_progress",
    "assigned_to": null,
    "tags": [],
    "metadata": {
      "source": "api",
      "browser": null,
      "device_type": null
    },
    "id": "uuid",
    "created_at": "2026-06-18T12:00:00Z",
    "updated_at": "2026-06-18T12:05:00Z",
    "resolved_at": null,
    "classification_confidence": 1.0,
    "classification_reasoning": "Matched category 'technical_issue' keywords: ['crash']. Matched priority 'high' keywords: ['blocked']"
  }
]
```

---

## GET /tickets/{ticket_id}

### Response (200)

Same as Ticket model.

---

## PUT /tickets/{ticket_id}

Update ticket (partial).

### Request

```json
{
  "status": "resolved",
  "assigned_to": "agent-1",
  "priority": "high"
}
```

---

### Response (200)

```json
{
  "customer_id": "CUST-1001",
  "customer_email": "user@example.com",
  "customer_name": "John Doe",
  "subject": "Cannot access account",
  "description": "I cannot access my account after resetting my password and need assistance.",
  "category": "account_access",
  "priority": "high",
  "status": "resolved",
  "assigned_to": "agent-1",
  "tags": [],
  "metadata": {
    "source": "web_form",
    "browser": "Chrome",
    "device_type": "desktop"
  },
  "id": "uuid",
  "created_at": "2026-06-18T12:00:00Z",
  "updated_at": "2026-06-18T13:00:00Z",
  "resolved_at": "2026-06-18T13:00:00Z",
  "classification_confidence": 0.43,
  "classification_reasoning": "Matched category 'account_access' keywords: ['password', 'reset']. Matched priority 'urgent' keywords: ['cannot access']"
}
```

---

## DELETE /tickets/{ticket_id}

### Response

204 No Content

---

## POST /tickets/{ticket_id}/auto-classify

### Response (200)

```json
{
  "category": "account_access",
  "priority": "urgent",
  "confidence": 0.43,
  "reasoning": "Matched category 'account_access' keywords: ['login', 'password']. Matched priority 'urgent' keywords: ['cannot access']",
  "keywords_found": ["login", "password", "cannot access"]
}
```

---

# Error Responses

## 404

```json
{ "detail": "Ticket not found" }
```

---

## 400

```json
{ "detail": "Unsupported file format 'txt'. Use csv, json, or xml." }
```

---

## 422

```json
{
  "detail": [
    {
      "loc": ["body", "customer_email"],
      "msg": "value is not a valid email address",
      "type": "value_error"
    }
  ]
}
```

---

# Status Codes

| Code | Meaning          |
| ---- | ---------------- |
| 200  | OK               |
| 201  | Created          |
| 204  | Deleted          |
| 400  | Import error     |
| 404  | Not found        |
| 422  | Validation error |

---

# See Also

* ARCHITECTURE.md
* TESTING_GUIDE.md
