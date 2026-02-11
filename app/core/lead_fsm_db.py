"""
Database-Backed FSM
===================
Same FSM logic, but now it writes to PostgreSQL
Every transition is persisted. Crash-safe.
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Import database stuff
sys.path.insert(0, str(Path(__file__).parent.parent / "db"))
from database import async_session_factory
from models import Lead as LeadModel, LeadEvent as EventModel

# Import FSM states
from lead_states import LeadState, LeadEvent, TERMINAL_STATES, TRANSITIONS


class LeadFSM:
    """
    FSM that persists to PostgreSQL.
    Every transition = database write.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def apply_event(self, lead_id: str, event: LeadEvent, payload: dict = None):
        """
        Apply an event to a lead. 
        Now with database persistence!
        """
        payload = payload or {}
        
        # 1. Load current lead from database (with row lock to prevent race conditions)
        result = await self.session.execute(
            select(LeadModel).where(LeadModel.id == lead_id).with_for_update()
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            raise ValueError(f"Lead {lead_id} not found in database")
        
        current_state = LeadState(lead.state)
        
        # 2. Block terminal states
        if current_state in TERMINAL_STATES:
            raise ValueError(
                f"Lead {lead_id} is in terminal state {current_state}. "
                f"Cannot apply {event}."
            )
        
        # 3. Look up transition in our transition table
        next_state = TRANSITIONS.get((current_state, event))
        if next_state is None:
            raise ValueError(
                f"Illegal transition: {current_state} + {event}"
            )
        
        # 4. Create IMMUTABLE event log entry
        event_log = EventModel(
            id=uuid.uuid4(),
            lead_id=lead_id,
            from_state=current_state.value,
            event=event.value,
            to_state=next_state.value,
            payload=payload,
            occurred_at=datetime.now(timezone.utc),
        )
        self.session.add(event_log)
        
        # 5. Update lead's current state
        lead.state = next_state.value
        lead.state_entered_at = datetime.now(timezone.utc)
        lead.updated_at = datetime.now(timezone.utc)
        
        # 6. Commit to PostgreSQL
        await self.session.commit()
        
        print(f"✅ Lead {str(lead_id)[:8]}: {current_state.value} + {event.value} → {next_state.value}")
        print(f"   💾 Written to PostgreSQL")
        
        return next_state


async def demo():
    """
    Demo: Create a lead and move it through the entire pipeline.
    Everything gets written to PostgreSQL.
    """
    
    print("\n🚀 Starting Database-Backed FSM Demo\n")
    
    # Step 1: Create a new lead in the database
    async with async_session_factory() as session:
        lead = LeadModel(
            id=uuid.uuid4(),
            email="jane@techcorp.com",
            first_name="Jane",
            last_name="Smith",
            company="Tech Corp",
            state=LeadState.NEW.value,
        )
        session.add(lead)
        await session.commit()
        
        print(f"🆕 Created lead in PostgreSQL:")
        print(f"   ID: {lead.id}")
        print(f"   Email: {lead.email}")
        print(f"   Company: {lead.company}")
        print(f"   Initial state: {lead.state}\n")
        
        lead_id = str(lead.id)
    
    # Step 2: Move it through the pipeline
    print("📊 Moving through state machine...\n")
    
    async with async_session_factory() as session:
        fsm = LeadFSM(session)
        
        await fsm.apply_event(lead_id, LeadEvent.VALIDATION_PASSED)
        
    async with async_session_factory() as session:
        fsm = LeadFSM(session)
        await fsm.apply_event(lead_id, LeadEvent.SCORE_COMPUTED, {"score": 0.92, "tier": "A"})
        
    async with async_session_factory() as session:
        fsm = LeadFSM(session)
        await fsm.apply_event(lead_id, LeadEvent.QUEUED_FOR_OUTREACH)
        
    async with async_session_factory() as session:
        fsm = LeadFSM(session)
        await fsm.apply_event(lead_id, LeadEvent.MESSAGE_SENT, {"channel": "email", "touch": 1})
        
    async with async_session_factory() as session:
        fsm = LeadFSM(session)
        await fsm.apply_event(lead_id, LeadEvent.REPLY_RECEIVED, {"text": "Very interested! Let's talk."})
        
    async with async_session_factory() as session:
        fsm = LeadFSM(session)
        await fsm.apply_event(lead_id, LeadEvent.QUALIFICATION_STARTED)
        
    async with async_session_factory() as session:
        fsm = LeadFSM(session)
        await fsm.apply_event(lead_id, LeadEvent.BANT_COMPLETE, {
            "budget": "50k-100k",
            "authority": "VP Engineering",
            "need": "Struggling with lead quality",
            "timeline": "Q2 2026"
        })
        
    async with async_session_factory() as session:
        fsm = LeadFSM(session)
        await fsm.apply_event(lead_id, LeadEvent.CRM_SYNCED, {"crm_id": "hubspot_12345"})
    
    # Step 3: Read final state and full history from database
    print("\n" + "="*70)
    print("📍 READING FROM DATABASE (proving persistence)")
    print("="*70 + "\n")
    
    async with async_session_factory() as session:
        # Get final lead state
        result = await session.execute(
            select(LeadModel).where(LeadModel.id == lead_id)
        )
        final_lead = result.scalar_one()
        
        # Get all events
        events_result = await session.execute(
            select(EventModel)
            .where(EventModel.lead_id == lead_id)
            .order_by(EventModel.occurred_at)
        )
        events = events_result.scalars().all()
    
    print(f"Final Lead State:")
    print(f"  Email: {final_lead.email}")
    print(f"  Company: {final_lead.company}")
    print(f"  Current State: {final_lead.state}")
    print(f"  Last Updated: {final_lead.updated_at}")
    
    print(f"\n📜 Complete Audit Trail ({len(events)} events):")
    for i, e in enumerate(events, 1):
        print(f"  {i}. {e.from_state:15} → {e.to_state:15} via {e.event}")
        if e.payload:
            print(f"     Payload: {e.payload}")
    
    print(f"\n" + "="*70)
    print("✅ SUCCESS: All data persisted to PostgreSQL!")
    print("="*70)
    print("\n💡 Try this:")
    print("   1. Stop this program")
    print("   2. Restart your computer")
    print("   3. Query the database - the lead is still there!")
    print("\n   That's crash-safety.\n")


if __name__ == "__main__":
    asyncio.run(demo())