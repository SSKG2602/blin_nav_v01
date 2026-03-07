from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.schemas.agent_log import AgentStepType
from app.schemas.session import Merchant, SessionStatus


class SessionORM(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    merchant = Column(String(64), nullable=False, default=Merchant.AMAZON.value)
    status = Column(String(32), nullable=False, default=SessionStatus.ACTIVE.value)
    locale = Column(String(16), nullable=True)
    screen_reader = Column(String(64), nullable=True)
    client_version = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    logs = relationship(
        "AgentLogORM",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    context = relationship(
        "SessionContextORM",
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )


class AgentLogORM(Base):
    __tablename__ = "agent_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    step_type = Column(String(32), nullable=False, default=AgentStepType.META.value)
    state_before = Column(String(64), nullable=True)
    state_after = Column(String(64), nullable=True)
    tool_name = Column(String(128), nullable=True)
    tool_input_excerpt = Column(String(512), nullable=True)
    tool_output_excerpt = Column(String(512), nullable=True)
    low_confidence = Column(Boolean, nullable=False, default=False)
    human_checkpoint = Column(Boolean, nullable=False, default=False)
    user_spoken_summary = Column(String(512), nullable=True)
    error_type = Column(String(128), nullable=True)
    error_message = Column(String(512), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    session = relationship("SessionORM", back_populates="logs")


class SessionContextORM(Base):
    __tablename__ = "session_contexts"

    session_id = Column(String(36), ForeignKey("sessions.id"), primary_key=True)
    latest_intent_json = Column(JSON, nullable=True)
    latest_product_intent_json = Column(JSON, nullable=True)
    latest_page_understanding_json = Column(JSON, nullable=True)
    latest_verification_json = Column(JSON, nullable=True)
    latest_multimodal_assessment_json = Column(JSON, nullable=True)
    latest_sensitive_checkpoint_json = Column(JSON, nullable=True)
    latest_low_confidence_status_json = Column(JSON, nullable=True)
    latest_recovery_status_json = Column(JSON, nullable=True)
    latest_trust_assessment_json = Column(JSON, nullable=True)
    latest_review_assessment_json = Column(JSON, nullable=True)
    latest_final_purchase_confirmation_json = Column(JSON, nullable=True)
    latest_post_purchase_summary_json = Column(JSON, nullable=True)
    latest_spoken_summary = Column(String(1024), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    session = relationship("SessionORM", back_populates="context")
