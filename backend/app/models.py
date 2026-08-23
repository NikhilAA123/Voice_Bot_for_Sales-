from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Text, String, DateTime, ForeignKey, Numeric, JSON
from .db import Base


def _now():
    return datetime.now(timezone.utc)


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_number = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="new")
    summary = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_sid = Column(Text, unique=True, nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"))
    started_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    ended_at = Column(DateTime(timezone=True))
    language = Column(Text)
    status = Column(Text, nullable=False, default="in_progress")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_id = Column(Integer, ForeignKey("calls.id", ondelete="CASCADE"), nullable=False)
    speaker = Column(Text, nullable=False)  # PRD §12 "role": customer | bot
    content = Column(Text, nullable=False)
    seq_number = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)


class Requirement(Base):
    __tablename__ = "requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_id = Column(Integer, ForeignKey("calls.id", ondelete="CASCADE"), nullable=False)
    business_type = Column(Text)
    product_or_service = Column(Text)
    product_count = Column(Integer)
    features = Column(JSON, default=list)  # PRD §8: missing fields stay unknown/null
    budget = Column(Text)
    timeline = Column(Text)
    decision_maker = Column(Text)
    pain_points = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class LeadDecision(Base):
    __tablename__ = "lead_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_id = Column(Integer, ForeignKey("calls.id", ondelete="CASCADE"), nullable=False)
    intent = Column(Text, nullable=False)  # HOT | WARM | COLD
    confidence = Column(Numeric(5, 2))
    signals = Column(JSON, default=list)
    barrier = Column(Text)
    next_action = Column(Text)
    raw_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)


class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    call_id = Column(Integer, ForeignKey("calls.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)
    idem_key = Column(Text, nullable=False, unique=True)
    status = Column(Text, nullable=False, default="pending")  # pending | sent/ok | failed
    provider_id = Column(Text)  # Twilio message SID etc.
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class Callback(Base):
    __tablename__ = "callbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    timezone = Column(Text, nullable=False, default="Asia/Kolkata")
    status = Column(Text, nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
