"""
Clause Models
=============

Models for clause extraction and playbook definitions.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
import uuid


class ClauseType(str, Enum):
    ASSIGNMENT_CONSENT = "assignment_consent"
    CHANGE_OF_CONTROL = "change_of_control"
    TERM_RENEWAL = "term_renewal"
    TERMINATION_NOTICE = "termination_notice"
    LIABILITY_CAP = "liability_cap"
    GOVERNING_LAW = "governing_law"
    MFN_EXCLUSIVITY = "mfn_exclusivity"
    SEVERANCE = "severance"
    NON_COMPETE = "non_compete"
    IP_LICENSE = "ip_license"


CLAUSE_LABELS = {
    ClauseType.ASSIGNMENT_CONSENT: "Assignment/Consent",
    ClauseType.CHANGE_OF_CONTROL: "Change of Control",
    ClauseType.TERM_RENEWAL: "Term/Renewal",
    ClauseType.TERMINATION_NOTICE: "Termination/Notice",
    ClauseType.LIABILITY_CAP: "Liability Cap",
    ClauseType.GOVERNING_LAW: "Governing Law",
    ClauseType.MFN_EXCLUSIVITY: "MFN/Exclusivity",
    ClauseType.SEVERANCE: "Severance",
    ClauseType.NON_COMPETE: "Non-Compete",
    ClauseType.IP_LICENSE: "IP License Type",
}


@dataclass
class ClauseExtraction:
    """A single extracted clause from a document."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str = ""
    doc_title: str = ""
    clause_type: ClauseType = ClauseType.ASSIGNMENT_CONSENT
    extracted_value: str = ""  # The key finding (e.g., "Consent required")
    snippet: str = ""          # Full text snippet containing the clause
    page_number: int = 1
    confidence: float = 0.0
    verified: bool = False
    flagged: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "doc_id": self.doc_id,
            "doc_title": self.doc_title,
            "clause_type": self.clause_type.value,
            "extracted_value": self.extracted_value,
            "snippet": self.snippet,
            "page_number": self.page_number,
            "confidence": self.confidence,
            "verified": self.verified,
            "flagged": self.flagged,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ClauseExtraction":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            doc_id=data["doc_id"],
            doc_title=data.get("doc_title", ""),
            clause_type=ClauseType(data["clause_type"]),
            extracted_value=data.get("extracted_value", ""),
            snippet=data.get("snippet", ""),
            page_number=data.get("page_number", 1),
            confidence=data.get("confidence", 0.0),
            verified=data.get("verified", False),
            flagged=data.get("flagged", False),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
        )


@dataclass
class Playbook:
    """Definition of a clause extraction playbook."""
    id: str
    name: str
    description: str
    doc_types: List[str]  # Which doc types this applies to
    clause_types: List[ClauseType]  # Which clauses to extract
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "doc_types": self.doc_types,
            "clause_types": [c.value for c in self.clause_types],
        }


# Predefined playbooks
PLAYBOOKS = [
    Playbook(
        id="customer_contracts",
        name="Customer Contracts",
        description="Extract key clauses from customer agreements (MSAs, SaaS, etc.)",
        doc_types=["Software License / SaaS", "NDA / Confidentiality Agreement", "Vendor Contract", "Unclassified"],
        clause_types=[
            ClauseType.ASSIGNMENT_CONSENT,
            ClauseType.CHANGE_OF_CONTROL,
            ClauseType.TERM_RENEWAL,
            ClauseType.TERMINATION_NOTICE,
            ClauseType.LIABILITY_CAP,
            ClauseType.GOVERNING_LAW,
            ClauseType.NON_COMPETE,
        ],
    ),
    Playbook(
        id="leases",
        name="Real Estate Leases",
        description="Extract key clauses from commercial leases",
        doc_types=["Commercial Lease"],
        clause_types=[
            ClauseType.ASSIGNMENT_CONSENT,
            ClauseType.TERM_RENEWAL,
            ClauseType.TERMINATION_NOTICE,
            ClauseType.GOVERNING_LAW,
        ],
    ),
    Playbook(
        id="employment",
        name="Employment Agreements",
        description="Extract key clauses from employment contracts",
        doc_types=["Employment Agreement"],
        clause_types=[
            ClauseType.CHANGE_OF_CONTROL,
            ClauseType.SEVERANCE,
            ClauseType.NON_COMPETE,
            ClauseType.TERM_RENEWAL,
            ClauseType.TERMINATION_NOTICE,
        ],
    ),
    Playbook(
        id="vendor",
        name="Vendor Contracts",
        description="Extract key clauses from vendor/supplier agreements",
        doc_types=["Vendor Contract", "Software License / SaaS"],
        clause_types=[
            ClauseType.ASSIGNMENT_CONSENT,
            ClauseType.TERMINATION_NOTICE,
            ClauseType.LIABILITY_CAP,
            ClauseType.GOVERNING_LAW,
        ],
    ),
    Playbook(
        id="ip",
        name="IP Agreements",
        description="Extract key clauses from IP and license agreements",
        doc_types=["Patent", "Trademark", "IP"],
        clause_types=[
            ClauseType.ASSIGNMENT_CONSENT,
            ClauseType.IP_LICENSE,
            ClauseType.MFN_EXCLUSIVITY,
            ClauseType.TERM_RENEWAL,
        ],
    ),
]


def get_playbook(playbook_id: str) -> Optional[Playbook]:
    """Get a playbook by ID."""
    for pb in PLAYBOOKS:
        if pb.id == playbook_id:
            return pb
    return None
