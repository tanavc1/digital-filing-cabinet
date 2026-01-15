"""
Review Models
=============

Models for document review workflow in M&A due diligence.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import uuid


class ReviewStatus(str, Enum):
    UNREVIEWED = "unreviewed"
    IN_REVIEW = "in_review"
    REVIEWED = "reviewed"
    QA_NEEDED = "qa_needed"
    QA_APPROVED = "qa_approved"
    FLAGGED = "flagged"


@dataclass
class DocumentReview:
    """Review state for a document in the diligence workflow."""
    doc_id: str
    status: ReviewStatus = ReviewStatus.UNREVIEWED
    assigned_to: Optional[str] = None
    reviewer_notes: str = ""
    reviewed_at: Optional[datetime] = None
    confidence: float = 0.0  # AI confidence 0-1
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "reviewer_notes": self.reviewer_notes,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "DocumentReview":
        return cls(
            doc_id=data["doc_id"],
            status=ReviewStatus(data.get("status", "unreviewed")),
            assigned_to=data.get("assigned_to"),
            reviewer_notes=data.get("reviewer_notes", ""),
            reviewed_at=datetime.fromisoformat(data["reviewed_at"]) if data.get("reviewed_at") else None,
            confidence=data.get("confidence", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
        )
