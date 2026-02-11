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