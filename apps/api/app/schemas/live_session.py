from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.session import Merchant


class LiveEventType(str, Enum):
    START = "start"
    USER_TEXT = "user_text"
    AUDIO_CHUNK = "audio_chunk"
    INTERRUPT = "interrupt"
    CANCEL = "cancel"
    CHECKPOINT_RESPONSE = "checkpoint_response"
    FINAL_CONFIRMATION_RESPONSE = "final_confirmation_response"
    PING = "ping"


class LiveSessionCreateRequest(BaseModel):
    merchant: Merchant = Merchant.AMAZON
    locale: str | None = None


class LiveSessionCreateResponse(BaseModel):
    session_id: UUID
    websocket_path: str
    locale: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LiveSpeechPayload(BaseModel):
    text: str
    audio_base64: str | None = None
    provider: str = "fallback"
    locale: str | None = None
    playback_mode: str | None = None


class LiveGatewayEvent(BaseModel):
    event: str
    data: dict[str, Any] = Field(default_factory=dict)
