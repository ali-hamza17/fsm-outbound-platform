"""
Autonomous Outbound Sales Platform - API
=========================================
FastAPI application for lead ingestion and management
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid

# Database imports
sys.path.insert(0, str(Path(__file__).parent.parent / "app" / "db"))
from database import async_session_factory
from models import Lead as LeadModel, LeadEvent as EventModel

# FSM imports
sys.path.insert(0, str(Path(__file__).parent.parent / "app" / "core"))
from lead_states import LeadState, LeadEvent
sys.path.insert(0, str(Path(__file__).parent.parent / "app" / "prospecting"))
from pipeline import ProspectingPipeline, RawLead

from sqlalchemy import select


app = FastAPI(
    title="Autonomous Outbound Sales Platform",
    description="FSM-driven lead management and outreach",
    version="1.0.0"
)


# ── Request/Response Models ───────────────────────────────────────────────────

class LeadCreateRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    industry: Optional[str] = None
    source_id: str = "api"


class LeadResponse(BaseModel):
    id: str
    email: Optional[str]
    first_name: Optional[str]
    company: Optional[str]
    state: str
    created_at: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "Autonomous Outbound Sales Platform",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/leads")
async def create_lead(lead: LeadCreateRequest):
    """
    Ingest a single lead through the prospecting pipeline.
    
    The lead will be:
    1. Validated (email format, required fields)
    2. Deduplicated (checked against existing leads)
    3. Scored against ICP criteria
    4. Stored in database with initial state
    """
    
    # Convert to RawLead
    raw = RawLead(
        email=lead.email,
        phone=lead.phone,
        first_name=lead.first_name,
        last_name=lead.last_name,
        company=lead.company,
        title=lead.title,
        industry=lead.industry,
    )
    
    # Run through pipeline
    pipeline = ProspectingPipeline(
        session_factory=async_session_factory,
        source_id=lead.source_id
    )
    
    result = await pipeline.ingest_lead(raw)
    
    return {
        "status": result.get("status"),
        "lead_id": result.get("lead_id"),
        "message": result.get("message", "Lead processed"),
        "details": result
    }


@app.get("/leads/{lead_id}")
async def get_lead(lead_id: str):
    """Get current state of a lead"""
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(LeadModel).where(LeadModel.id == lead_id)
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        return {
            "id": str(lead.id),
            "email": lead.email,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "company": lead.company,
            "state": lead.state,
            "state_entered_at": lead.state_entered_at.isoformat() if lead.state_entered_at else None,
            "created_at": lead.created_at.isoformat(),
            "updated_at": lead.updated_at.isoformat(),
        }


@app.get("/leads/{lead_id}/history")
async def get_lead_history(lead_id: str):
    """Get full event history for a lead (audit trail)"""
    
    async with async_session_factory() as session:
        # Check lead exists
        lead_result = await session.execute(
            select(LeadModel).where(LeadModel.id == lead_id)
        )
        lead = lead_result.scalar_one_or_none()
        
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # Get all events
        events_result = await session.execute(
            select(EventModel)
            .where(EventModel.lead_id == lead_id)
            .order_by(EventModel.occurred_at)
        )
        events = events_result.scalars().all()
        
        return {
            "lead_id": lead_id,
            "current_state": lead.state,
            "event_count": len(events),
            "events": [
                {
                    "from_state": e.from_state,
                    "event": e.event,
                    "to_state": e.to_state,
                    "payload": e.payload,
                    "occurred_at": e.occurred_at.isoformat(),
                }
                for e in events
            ]
        }


@app.get("/leads")
async def list_leads(limit: int = 10, state: Optional[str] = None):
    """List leads with optional state filter"""
    
    async with async_session_factory() as session:
        query = select(LeadModel).limit(limit)
        
        if state:
            query = query.where(LeadModel.state == state)
        
        result = await session.execute(query)
        leads = result.scalars().all()
        
        return {
            "count": len(leads),
            "leads": [
                {
                    "id": str(lead.id),
                    "email": lead.email,
                    "company": lead.company,
                    "state": lead.state,
                    "created_at": lead.created_at.isoformat(),
                }
                for lead in leads
            ]
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)