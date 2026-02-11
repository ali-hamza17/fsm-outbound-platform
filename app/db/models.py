"""
Database Models
===============
Lead = current state + data
LeadEvent = immutable history (audit log)
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Lead(Base):
    """
    The Lead table stores the CURRENT state.
    Think of it as a snapshot: where is this lead RIGHT NOW?
    """
    __tablename__ = "leads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Lead data
    email = Column(String(320), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    company = Column(String(255), nullable=True)
    
    # FSM state - THE SINGLE SOURCE OF TRUTH
    state = Column(String(50), nullable=False, default="NEW")
    state_entered_at = Column(DateTime(timezone=True), default=utcnow)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    
    # Relationship to events
    events = relationship("LeadEvent", back_populates="lead", order_by="LeadEvent.occurred_at")


class LeadEvent(Base):
    """
    The Event Log - IMMUTABLE history.
    Every state transition creates a new row here.
    Never updated or deleted - append-only.
    """
    __tablename__ = "lead_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    
    # What happened?
    from_state = Column(String(50), nullable=False)
    event = Column(String(100), nullable=False)
    to_state = Column(String(50), nullable=False)
    
    # Extra data (scores, messages, etc.)
    payload = Column(JSON, nullable=True)
    
    # When?
    occurred_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    
    # Relationship
    lead = relationship("Lead", back_populates="events")