"""
Issue Models
============

Models for tracking issues found during diligence.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import uuid


class IssueSeverity(str, Enum):
    CRITICAL = "critical"  # Red - deal breaker
    WARNING = "warning"    # Yellow - needs attention
    INFO = "info"          # Green - FYI


class IssueStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"


@dataclass
class Issue:
    """An issue found during due diligence."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    severity: IssueSeverity = IssueSeverity.WARNING
    status: IssueStatus = IssueStatus.OPEN
    
    # Links
    doc_id: Optional[str] = None
    doc_title: Optional[str] = None
    clause_id: Optional[str] = None  # Link to specific clause/evidence
    
    # Assignment
    owner: Optional[str] = None
    action_required: str = ""
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "status": self.status.value,
            "doc_id": self.doc_id,
            "doc_title": self.doc_title,
            "clause_id": self.clause_id,
            "owner": self.owner,
            "action_required": self.action_required,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Issue":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", ""),
            description=data.get("description", ""),
            severity=IssueSeverity(data.get("severity", "warning")),
            status=IssueStatus(data.get("status", "open")),
            doc_id=data.get("doc_id"),
            doc_title=data.get("doc_title"),
            clause_id=data.get("clause_id"),
            owner=data.get("owner"),
            action_required=data.get("action_required", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            resolved_at=datetime.fromisoformat(data["resolved_at"]) if data.get("resolved_at") else None,
        )
