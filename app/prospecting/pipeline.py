"""
Prospecting Pipeline
====================
Ingests, validates, deduplicates, scores leads
Then writes to database via FSM
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import hashlib
import re
import uuid as _uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select

# Import database models
sys.path.insert(0, str(Path(__file__).parent.parent / "db"))
from models import Lead as LeadModel, LeadEvent as EventModel

# Import FSM
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from lead_states import LeadState, LeadEvent


# ── Raw Lead Structure ────────────────────────────────────────────────────────

@dataclass
class RawLead:
    """Lead before validation"""
    email: str | None = None
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    title: str | None = None
    industry: str | None = None


# ── Validation ────────────────────────────────────────────────────────────────

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
ROLE_EMAILS = {"info@", "contact@", "hello@", "support@", "admin@"}
DISPOSABLE_DOMAINS = {"mailinator.com", "guerrillamail.com", "temp-mail.org"}


def sanitize_lead(raw: RawLead) -> dict:
    """Validate and clean a raw lead"""
    errors = []
    
    if not raw.email and not raw.phone:
        return {"valid": False, "errors": ["missing_contact"]}
    
    email = None
    if raw.email:
        email = raw.email.strip().lower()
        
        if not EMAIL_REGEX.match(email):
            errors.append(f"invalid_email: {email}")
        else:
            domain = email.split("@")[1]
            if domain in DISPOSABLE_DOMAINS:
                errors.append(f"disposable_domain: {domain}")
            elif any(email.startswith(prefix) for prefix in ROLE_EMAILS):
                errors.append(f"role_email: {email}")
    
    if errors:
        return {"valid": False, "errors": errors}
    
    return {"valid": True, "email": email}


# ── Deduplication ─────────────────────────────────────────────────────────────

def compute_fingerprint(email: str | None) -> str:
    """Generate dedup hash"""
    key = (email or "").lower().strip()
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# ── Scoring ───────────────────────────────────────────────────────────────────

def score_lead(raw: RawLead) -> tuple[float, dict]:
    """Score against ICP"""
    breakdown = {}
    
    # Industry (0-30 pts)
    industry = (raw.industry or "").lower()
    target_industries = ["saas", "fintech", "tech"]
    breakdown["industry"] = 0.3 if any(t in industry for t in target_industries) else 0.05
    
    # Title (0-30 pts)
    title = (raw.title or "").lower()
    target_titles = ["ceo", "cto", "vp", "director", "head"]
    breakdown["title"] = 0.3 if any(t in title for t in target_titles) else 0.05
    
    # Completeness (0-40 pts)
    fields = [raw.email, raw.first_name, raw.company, raw.title, raw.industry]
    filled = sum(1 for f in fields if f)
    breakdown["completeness"] = (filled / len(fields)) * 0.4
    
    total = sum(breakdown.values())
    
    if total >= 0.65:
        tier = "A"
    elif total >= 0.45:
        tier = "B"
    elif total >= 0.25:
        tier = "C"
    else:
        tier = "D"
    
    return round(total, 2), {**breakdown, "tier": tier}


# ── Pipeline ──────────────────────────────────────────────────────────────────

class ProspectingPipeline:
    """Full pipeline: validate → dedupe → score → persist"""
    
    def __init__(self, session_factory, source_id: str):
        self.session_factory = session_factory
        self.source_id = source_id
    
    async def ingest_lead(self, raw: RawLead) -> dict:
        """Process a single lead through the full pipeline"""
        
        # 1. Validate
        validation = sanitize_lead(raw)
        if not validation["valid"]:
            return {
                "status": "rejected",
                "reason": "validation_failed",
                "errors": validation.get("errors")
            }
        
        email = validation["email"]
        fingerprint = compute_fingerprint(email)
        
        # 2. Check for duplicate
        async with self.session_factory() as session:
            result = await session.execute(
                select(LeadModel).where(LeadModel.email == email)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                return {
                    "status": "duplicate",
                    "lead_id": str(existing.id),
                    "message": "Lead already exists"
                }
            
            # 3. Score
            score, breakdown = score_lead(raw)
            
            # 4. Create lead in database
            lead = LeadModel(
                id=_uuid.uuid4(),
                email=email,
                first_name=raw.first_name,
                last_name=raw.last_name,
                company=raw.company,
                title=raw.title,
                industry=raw.industry,
                state=LeadState.NEW.value,
            )
            session.add(lead)
            
            # Create initial event
            event = EventModel(
                id=_uuid.uuid4(),
                lead_id=lead.id,
                from_state="NONE",
                event="LEAD_CREATED",
                to_state=LeadState.NEW.value,
                payload={"score": score, "tier": breakdown.get("tier"), "source": self.source_id},
                occurred_at=datetime.now(timezone.utc),
            )
            session.add(event)
            
            await session.commit()
            lead_id = str(lead.id)
        
        return {
            "status": "created",
            "lead_id": lead_id,
            "score": score,
            "tier": breakdown.get("tier"),
            "message": "Lead successfully ingested"
        }