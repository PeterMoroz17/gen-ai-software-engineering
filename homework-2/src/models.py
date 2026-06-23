from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class Category(str, Enum):
    account_access = "account_access"
    technical_issue = "technical_issue"
    billing_question = "billing_question"
    feature_request = "feature_request"
    bug_report = "bug_report"
    other = "other"


class Priority(str, Enum):
    urgent = "urgent"
    high = "high"
    medium = "medium"
    low = "low"


class Status(str, Enum):
    new = "new"
    in_progress = "in_progress"
    waiting_customer = "waiting_customer"
    resolved = "resolved"
    closed = "closed"


class Source(str, Enum):
    web_form = "web_form"
    email = "email"
    api = "api"
    chat = "chat"
    phone = "phone"


class DeviceType(str, Enum):
    desktop = "desktop"
    mobile = "mobile"
    tablet = "tablet"


class Metadata(BaseModel):
    source: Source = Source.api
    browser: Optional[str] = None
    device_type: Optional[DeviceType] = None


class TicketCreate(BaseModel):
    customer_id: str
    customer_email: EmailStr
    customer_name: str
    subject: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=10, max_length=2000)
    category: Optional[Category] = None
    priority: Optional[Priority] = None
    status: Status = Status.new
    assigned_to: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    metadata: Metadata = Field(default_factory=Metadata)

    @field_validator("customer_id", "customer_name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v


class TicketUpdate(BaseModel):
    customer_email: Optional[EmailStr] = None
    customer_name: Optional[str] = None
    subject: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10, max_length=2000)
    category: Optional[Category] = None
    priority: Optional[Priority] = None
    status: Optional[Status] = None
    assigned_to: Optional[str] = None
    tags: Optional[list[str]] = None
    metadata: Optional[Metadata] = None


class Ticket(TicketCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    classification_confidence: Optional[float] = None
    classification_reasoning: Optional[str] = None


class ImportSummary(BaseModel):
    total: int
    successful: int
    failed: int
    errors: list[dict] = Field(default_factory=list)


class ClassificationResult(BaseModel):
    category: Category
    priority: Priority
    confidence: float
    reasoning: str
    keywords_found: list[str]
