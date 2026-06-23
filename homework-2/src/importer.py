from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ET
from typing import Any

from pydantic import ValidationError

from .models import ImportSummary, Ticket, TicketCreate


def _normalize_metadata(raw: Any) -> dict:
    """Coerce a metadata value from any parsed shape into a dict."""
    if isinstance(raw, dict):
        return raw
    return {}


def _normalize_tags(raw: Any) -> list:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()]
    return []


def parse_csv(data: bytes) -> list[dict]:
    text = data.decode("utf-8-sig")  # handle optional BOM
    reader = csv.DictReader(io.StringIO(text))
    records = []
    for row in reader:
        record = {k.strip(): v.strip() for k, v in row.items() if k}
        # tags stored as comma-separated string in CSV
        if "tags" in record:
            record["tags"] = _normalize_tags(record["tags"])
        # metadata sub-fields may be flattened as metadata.source etc.
        meta: dict = {}
        flat_meta_keys = [k for k in record if k.startswith("metadata.")]
        for key in flat_meta_keys:
            sub = key[len("metadata."):]
            meta[sub] = record.pop(key)
        if meta:
            record["metadata"] = meta
        records.append(record)
    return records


def parse_json(data: bytes) -> list[dict]:
    payload = json.loads(data.decode("utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("tickets", "data", "records"):
            if key in payload and isinstance(payload[key], list):
                return payload[key]
    raise ValueError("JSON must be an array or an object with a 'tickets' array")


def parse_xml(data: bytes) -> list[dict]:
    root = ET.fromstring(data.decode("utf-8"))
    # root may be <tickets> wrapper or a single <ticket>
    ticket_els = root.findall("ticket") if root.tag != "ticket" else [root]
    records = []
    for el in ticket_els:
        record: dict = {}
        for child in el:
            if child.tag == "tags":
                record["tags"] = [t.text for t in child.findall("tag") if t.text]
            elif child.tag == "metadata":
                meta = {}
                for m in child:
                    meta[m.tag] = m.text
                record["metadata"] = meta
            else:
                record[child.tag] = child.text
        records.append(record)
    return records


def import_records(raw_records: list[dict]) -> tuple[list[Ticket], ImportSummary]:
    successful: list[Ticket] = []
    errors: list[dict] = []

    for idx, record in enumerate(raw_records):
        # coerce nested types before validation
        if "tags" in record:
            record["tags"] = _normalize_tags(record["tags"])
        if "metadata" in record:
            record["metadata"] = _normalize_metadata(record["metadata"])

        try:
            create = TicketCreate.model_validate(record)
            ticket = Ticket(**create.model_dump())
            successful.append(ticket)
        except ValidationError as exc:
            errors.append({
                "index": idx,
                "record": record,
                "error": exc.errors(include_url=False),
            })
        except Exception as exc:
            errors.append({"index": idx, "record": record, "error": str(exc)})

    summary = ImportSummary(
        total=len(raw_records),
        successful=len(successful),
        failed=len(errors),
        errors=errors,
    )
    return successful, summary
