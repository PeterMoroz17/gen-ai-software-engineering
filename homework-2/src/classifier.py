from __future__ import annotations

from .models import Category, ClassificationResult, Priority

_CATEGORY_KEYWORDS: dict[Category, list[str]] = {
    Category.account_access: [
        "login", "log in", "log-in", "password", "2fa", "two factor", "two-factor",
        "locked", "lock out", "lockout", "sign in", "sign-in", "signin",
        "authentication", "authenticate", "account access", "reset", "forgot",
        "credentials", "username", "session", "logout", "log out",
    ],
    Category.technical_issue: [
        "error", "crash", "crashing", "not working", "doesn't work", "broken",
        "exception", "failure", "fails", "timeout", "timed out", "outage",
        "down", "unavailable", "slow", "hang", "hangs", "freeze", "freezing",
        "500", "internal server error", "502", "503",
    ],
    Category.billing_question: [
        "payment", "pay", "invoice", "charge", "charged", "refund", "subscription",
        "billing", "bill", "receipt", "overcharged", "overcharge", "price",
        "pricing", "cost", "fee", "credit card", "debit", "plan", "upgrade",
        "downgrade", "cancel", "cancellation",
    ],
    Category.feature_request: [
        "feature", "suggestion", "suggest", "enhancement", "enhance",
        "would be nice", "could you add", "please add", "request", "wishlist",
        "idea", "improvement", "improve", "new functionality", "support for",
        "allow us", "ability to",
    ],
    Category.bug_report: [
        "bug", "defect", "reproduce", "steps to reproduce", "regression",
        "unexpected behavior", "unexpected behaviour", "wrong output", "incorrect",
        "misbehaving", "reproducible", "repro", "workaround", "glitch",
    ],
}

_PRIORITY_KEYWORDS: dict[Priority, list[str]] = {
    Priority.urgent: [
        "can't access", "cannot access", "critical", "production down",
        "prod down", "security breach", "data loss", "data breach", "outage",
    ],
    Priority.high: [
        "important", "blocking", "blocked", "asap", "as soon as possible",
        "high priority", "top priority", "escalate",
    ],
    Priority.low: [
        "minor", "cosmetic", "suggestion", "nice to have", "nice-to-have",
        "when possible", "whenever", "low priority", "not urgent", "someday",
    ],
}


def classify(subject: str, description: str) -> ClassificationResult:
    text = f"{subject} {description}".lower()

    # --- category scoring ---
    category_hits: dict[Category, list[str]] = {}
    category_scores: dict[Category, float] = {}

    for cat, keywords in _CATEGORY_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in text]
        category_hits[cat] = hits
        category_scores[cat] = len(hits) / len(keywords)

    best_category = max(category_scores, key=lambda c: category_scores[c])
    best_score = category_scores[best_category]

    if best_score == 0.0:
        best_category = Category.other
        confidence = 0.0
        category_keywords_found: list[str] = []
    else:
        confidence = min(best_score * 5, 1.0)  # scale up: 20% keyword hit → 1.0 confidence
        category_keywords_found = category_hits[best_category]

    # --- priority scoring ---
    priority_hits: dict[Priority, list[str]] = {}
    for pri, keywords in _PRIORITY_KEYWORDS.items():
        priority_hits[pri] = [kw for kw in keywords if kw in text]

    best_priority = Priority.medium
    for pri in (Priority.urgent, Priority.high, Priority.low):
        if priority_hits[pri]:
            best_priority = pri
            break

    priority_keywords_found = priority_hits.get(best_priority, [])
    all_keywords_found = list(dict.fromkeys(category_keywords_found + priority_keywords_found))

    # --- reasoning ---
    parts: list[str] = []
    if category_keywords_found:
        parts.append(f"Matched category '{best_category.value}' keywords: {category_keywords_found}")
    else:
        parts.append("No category keywords matched; defaulting to 'other'")
    if priority_keywords_found:
        parts.append(f"Matched priority '{best_priority.value}' keywords: {priority_keywords_found}")
    else:
        parts.append("No priority keywords matched; defaulting to 'medium'")

    return ClassificationResult(
        category=best_category,
        priority=best_priority,
        confidence=round(confidence, 4),
        reasoning=". ".join(parts),
        keywords_found=all_keywords_found,
    )
