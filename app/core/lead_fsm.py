"""
Lead State Machine
The exact same pattern as the coffee machine, but for leads
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

from lead_states import LeadState, LeadEvent, TERMINAL_STATES


# Define all legal transitions
TRANSITIONS = {
    # Prospecting pipeline
    (LeadState.NEW, LeadEvent.VALIDATION_PASSED): LeadState.VALIDATED,
    (LeadState.NEW, LeadEvent.VALIDATION_FAILED): LeadState.REJECTED,
    (LeadState.NEW, LeadEvent.DUPLICATE_FOUND): LeadState.DUPLICATE,
    
    (LeadState.VALIDATED, LeadEvent.SCORE_COMPUTED): LeadState.SCORED,
    (LeadState.SCORED, LeadEvent.QUEUED_FOR_OUTREACH): LeadState.QUEUED,
    
    # Outreach
    (LeadState.QUEUED, LeadEvent.MESSAGE_SENT): LeadState.CONTACTED,
    (LeadState.CONTACTED, LeadEvent.REPLY_RECEIVED): LeadState.REPLIED,
    (LeadState.CONTACTED, LeadEvent.SEQUENCE_EXHAUSTED): LeadState.NO_RESPONSE,
    (LeadState.CONTACTED, LeadEvent.OPT_OUT): LeadState.OPTED_OUT,
    
    # Qualification
    (LeadState.REPLIED, LeadEvent.QUALIFICATION_STARTED): LeadState.QUALIFYING,
    (LeadState.QUALIFYING, LeadEvent.BANT_COMPLETE): LeadState.QUALIFIED,
    (LeadState.QUALIFYING, LeadEvent.BANT_FAILED): LeadState.DISQUALIFIED,
    
    # Handoff
    (LeadState.QUALIFIED, LeadEvent.CRM_SYNCED): LeadState.HANDED_OFF,
}


@dataclass
class Lead:
    """
    Represents a single lead moving through the system.
    In production, this data lives in PostgreSQL.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: Optional[str] = None
    first_name: Optional[str] = None
    company: Optional[str] = None
    
    # FSM state
    current_state: LeadState = LeadState.NEW
    history: list = field(default_factory=list)
    
    def apply_event(self, event: LeadEvent, payload: dict = None):
        """
        Apply an event to this lead. Same logic as the coffee machine!
        """
        payload = payload or {}
        
        # Block transitions from terminal states
        if self.current_state in TERMINAL_STATES:
            raise ValueError(
                f"Lead {self.id} is in terminal state {self.current_state}. "
                f"Cannot apply {event}."
            )
        
        # Look up the transition
        next_state = TRANSITIONS.get((self.current_state, event))
        
        if next_state is None:
            raise ValueError(
                f"Illegal transition: {self.current_state} + {event}"
            )
        
        # Record what happened (audit trail)
        self.history.append({
            "from": self.current_state.value,
            "event": event.value,
            "to": next_state.value,
            "payload": payload,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Move to new state
        old_state = self.current_state
        self.current_state = next_state
        
        print(f"✅ Lead {self.id[:8]}: {old_state.value} + {event.value} → {next_state.value}")
        
        return next_state


# Demo: Watch a lead move through the entire pipeline
if __name__ == "__main__":
    lead = Lead(
        email="john@acmecorp.com",
        first_name="John",
        company="ACME Corp"
    )
    
    print(f"🆕 Created lead: {lead.id}")
    print(f"   Email: {lead.email}")
    print(f"   Initial state: {lead.current_state.value}\n")
    
    # Try to skip validation
try:
    lead.apply_event(LeadEvent.SCORE_COMPUTED)  # Can't score before validating!
except ValueError as e:
    print(f"\n🛑 Prevented bug: {e}\n")
    
    # Prospecting pipeline
    lead.apply_event(LeadEvent.VALIDATION_PASSED)
    lead.apply_event(LeadEvent.SCORE_COMPUTED, {"score": 0.85})
    lead.apply_event(LeadEvent.QUEUED_FOR_OUTREACH)
    
    # Outreach
    lead.apply_event(LeadEvent.MESSAGE_SENT, {"channel": "email", "touch": 1})
    lead.apply_event(LeadEvent.REPLY_RECEIVED, {"text": "Tell me more!"})
    
    # Qualification
    lead.apply_event(LeadEvent.QUALIFICATION_STARTED)
    lead.apply_event(LeadEvent.BANT_COMPLETE, {"budget": "50k", "timeline": "Q2"})
    
    # Handoff
    lead.apply_event(LeadEvent.CRM_SYNCED, {"crm_id": "hubspot_12345"})
    
    print(f"\n📍 Final state: {lead.current_state.value}")
    print(f"\n📜 Full journey ({len(lead.history)} steps):")
    for step in lead.history:
        print(f"   {step['from']:15} → {step['to']:15} via {step['event']}")
    
    print("\n❌ Now let's try something illegal:")
    try:
        # Can't move from terminal state!
        lead.apply_event(LeadEvent.MESSAGE_SENT)
    except ValueError as e:
        print(f"   ERROR: {e}")