from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Merchant(str, Enum):
    DEMO_STORE = "demo.nopcommerce.com"
    BIGBASKET = "bigbasket.com"
    AMAZON = "amazon.in"
    FLIPKART = "flipkart.com"
    MEESHO = "meesho.com"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"
    CANCELLED = "cancelled"
    ERROR = "error"


class SessionCreate(BaseModel):
    merchant: Merchant = Merchant.DEMO_STORE
    locale: str | None = None
    screen_reader: str | None = None
    client_version: str | None = None
    user_agent: str | None = None


class SessionSummary(BaseModel):
    session_id: UUID = Field(default_factory=uuid4)
    merchant: Merchant
    status: SessionStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)
    owner_display_name: str | None = None


class SessionDetail(SessionSummary):
    locale: str | None = None
    screen_reader: str | None = None
    client_version: str | None = None
    user_id: UUID | None = None
