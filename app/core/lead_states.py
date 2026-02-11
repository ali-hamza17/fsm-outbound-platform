"""
Lead Lifecycle States
Every lead is in exactly ONE of these states at any time
"""

from enum import Enum


class LeadState(str, Enum):
    # Prospecting pipeline
    NEW = "NEW"                    # Just ingested
    VALIDATED = "VALIDATED"        # Email/phone validated
    REJECTED = "REJECTED"          # Failed validation (terminal)
    DUPLICATE = "DUPLICATE"        # Already exists (terminal)
    SCORED = "SCORED"              # ICP score assigned
    QUEUED = "QUEUED"              # Ready for outreach
    
    # Outreach sequence
    CONTACTED = "CONTACTED"        # First message sent
    REPLIED = "REPLIED"            # They responded!
    NO_RESPONSE = "NO_RESPONSE"    # Sequence exhausted (terminal)
    OPTED_OUT = "OPTED_OUT"        # Unsubscribed (terminal)
    
    # Qualification
    QUALIFYING = "QUALIFYING"      # BANT conversation active
    QUALIFIED = "QUALIFIED"        # Passed BANT
    DISQUALIFIED = "DISQUALIFIED"  # Failed BANT (terminal)
    
    # Handoff
    HANDED_OFF = "HANDED_OFF"      # In CRM, human owns it


class LeadEvent(str, Enum):
    # Prospecting
    LEAD_CREATED = "LEAD_CREATED"
    VALIDATION_PASSED = "VALIDATION_PASSED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    DUPLICATE_FOUND = "DUPLICATE_FOUND"
    SCORE_COMPUTED = "SCORE_COMPUTED"
    QUEUED_FOR_OUTREACH = "QUEUED_FOR_OUTREACH"
    
    # Outreach
    MESSAGE_SENT = "MESSAGE_SENT"
    REPLY_RECEIVED = "REPLY_RECEIVED"
    SEQUENCE_EXHAUSTED = "SEQUENCE_EXHAUSTED"
    OPT_OUT = "OPT_OUT"
    
    # Qualification
    QUALIFICATION_STARTED = "QUALIFICATION_STARTED"
    BANT_COMPLETE = "BANT_COMPLETE"
    BANT_FAILED = "BANT_FAILED"
    
    # Handoff
    CRM_SYNCED = "CRM_SYNCED"


# Terminal states - once a lead reaches these, it stops moving
TERMINAL_STATES = {
    LeadState.REJECTED,
    LeadState.DUPLICATE,
    LeadState.NO_RESPONSE,
    LeadState.OPTED_OUT,
    LeadState.DISQUALIFIED,
}

# ... (all your existing code above)

# Add this at the very end:
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