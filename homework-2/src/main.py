from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Response, UploadFile, status

from .importer import import_records, parse_csv, parse_json, parse_xml
from .models import (
    Category,
    ClassificationResult,
    ImportSummary,
    Priority,
    Status,
    Ticket,
    TicketCreate,
    TicketUpdate,
)
from .storage import store

app = FastAPI(title="Customer Support Ticket System", version="1.0.0")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PARSERS = {
    "csv": parse_csv,
    "json": parse_json,
    "xml": parse_xml,
}


def _get_or_404(ticket_id: str) -> Ticket:
    ticket = store.get(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/tickets", status_code=status.HTTP_201_CREATED, response_model=Ticket)
def create_ticket(
    body: TicketCreate,
    auto_classify: bool = Query(default=False),
) -> Ticket:
    ticket = Ticket(**body.model_dump())
    if auto_classify:
        from .classifier import classify
        result = classify(ticket.subject, ticket.description)
        ticket.category = result.category
        ticket.priority = result.priority
        ticket.classification_confidence = result.confidence
        ticket.classification_reasoning = result.reasoning
    store.add(ticket)
    return ticket


@app.post("/tickets/import", response_model=ImportSummary)
async def import_tickets(
    file: UploadFile,
    auto_classify: bool = Query(default=False),
) -> ImportSummary:
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _PARSERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Use csv, json, or xml.",
        )
    data = await file.read()
    try:
        raw_records = _PARSERS[ext](data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse {ext.upper()} file: {exc}",
        )

    tickets, summary = import_records(raw_records)

    if auto_classify:
        from .classifier import classify
        for ticket in tickets:
            result = classify(ticket.subject, ticket.description)
            ticket.category = result.category
            ticket.priority = result.priority
            ticket.classification_confidence = result.confidence
            ticket.classification_reasoning = result.reasoning

    for ticket in tickets:
        store.add(ticket)

    return summary


@app.get("/tickets", response_model=list[Ticket])
def list_tickets(
    category: Optional[Category] = Query(default=None),
    priority: Optional[Priority] = Query(default=None),
    status_filter: Optional[Status] = Query(default=None, alias="status"),
) -> list[Ticket]:
    return store.list(category=category, priority=priority, status=status_filter)


@app.get("/tickets/{ticket_id}", response_model=Ticket)
def get_ticket(ticket_id: str) -> Ticket:
    return _get_or_404(ticket_id)


@app.put("/tickets/{ticket_id}", response_model=Ticket)
def update_ticket(ticket_id: str, body: TicketUpdate) -> Ticket:
    ticket = _get_or_404(ticket_id)
    update_data = body.model_dump(exclude_none=True)

    for field, value in update_data.items():
        setattr(ticket, field, value)

    ticket.updated_at = datetime.now(timezone.utc)

    # set resolved_at when transitioning to resolved
    if body.status == Status.resolved and ticket.resolved_at is None:
        ticket.resolved_at = datetime.now(timezone.utc)

    store.update(ticket)
    return ticket


@app.delete("/tickets/{ticket_id}")
def delete_ticket(ticket_id: str) -> Response:
    if not store.delete(ticket_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/tickets/{ticket_id}/auto-classify", response_model=ClassificationResult)
def auto_classify_ticket(ticket_id: str) -> ClassificationResult:
    ticket = _get_or_404(ticket_id)
    from .classifier import classify
    result = classify(ticket.subject, ticket.description)
    ticket.category = result.category
    ticket.priority = result.priority
    ticket.classification_confidence = result.confidence
    ticket.classification_reasoning = result.reasoning
    ticket.updated_at = datetime.now(timezone.utc)
    store.update(ticket)
    return result
