"""
Audit Templates
===============

Predefined audit templates for common due diligence scenarios.
Each template contains a set of risk-check questions that will be
run in parallel against a target folder.
"""

from typing import Dict, List, Any

# Risk severity levels
SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"
SEVERITY_INFO = "INFO"

# Finding status
STATUS_FOUND = "FOUND"
STATUS_NOT_FOUND = "NOT_FOUND"
STATUS_UNCLEAR = "UNCLEAR"


AUDIT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "commercial_lease": {
        "id": "commercial_lease",
        "name": "Commercial Lease Review",
        "description": "Standard review for commercial property leases",
        "questions": [
            {
                "text": "Is there a change of control clause that could be triggered by a sale or merger?",
                "severity": SEVERITY_HIGH,
                "category": "Control Provisions"
            },
            {
                "text": "What are the termination provisions and associated fees or penalties?",
                "severity": SEVERITY_HIGH,
                "category": "Termination"
            },
            {
                "text": "What is the lease term, commencement date, and expiration date?",
                "severity": SEVERITY_MEDIUM,
                "category": "Term"
            },
            {
                "text": "Are there any renewal or extension options? What are the terms?",
                "severity": SEVERITY_MEDIUM,
                "category": "Renewal Options"
            },
            {
                "text": "Are there any exclusivity provisions limiting competing businesses?",
                "severity": SEVERITY_MEDIUM,
                "category": "Exclusivity"
            },
            {
                "text": "What are the rent escalation provisions or rent adjustment mechanisms?",
                "severity": SEVERITY_MEDIUM,
                "category": "Financial Terms"
            },
            {
                "text": "Is there a personal guarantee requirement from principals?",
                "severity": SEVERITY_HIGH,
                "category": "Guarantees"
            },
            {
                "text": "What are the insurance requirements for the tenant?",
                "severity": SEVERITY_LOW,
                "category": "Insurance"
            },
            {
                "text": "Are there any restrictions on assignment or subletting?",
                "severity": SEVERITY_MEDIUM,
                "category": "Assignment"
            },
            {
                "text": "What are the landlord's rights of access to the premises?",
                "severity": SEVERITY_LOW,
                "category": "Access Rights"
            }
        ]
    },
    
    "ma_diligence": {
        "id": "ma_diligence",
        "name": "M&A Due Diligence",
        "description": "Key risk areas for mergers and acquisitions",
        "questions": [
            {
                "text": "Are there any change of control provisions that could be triggered by this transaction?",
                "severity": SEVERITY_HIGH,
                "category": "Change of Control"
            },
            {
                "text": "Are there any non-compete or non-solicitation agreements with key employees?",
                "severity": SEVERITY_HIGH,
                "category": "Employee Restrictions"
            },
            {
                "text": "What material contracts exist and are they assignable?",
                "severity": SEVERITY_HIGH,
                "category": "Contracts"
            },
            {
                "text": "Are there any pending or threatened litigation matters?",
                "severity": SEVERITY_HIGH,
                "category": "Litigation"
            },
            {
                "text": "What intellectual property rights are owned or licensed?",
                "severity": SEVERITY_MEDIUM,
                "category": "IP Rights"
            },
            {
                "text": "Are there any outstanding loans, liens, or security interests?",
                "severity": SEVERITY_HIGH,
                "category": "Debt & Liens"
            },
            {
                "text": "What are the key customer contracts and their terms?",
                "severity": SEVERITY_MEDIUM,
                "category": "Customer Contracts"
            },
            {
                "text": "Are there any material supplier or vendor agreements?",
                "severity": SEVERITY_MEDIUM,
                "category": "Supplier Contracts"
            },
            {
                "text": "What regulatory licenses or permits are required for the business?",
                "severity": SEVERITY_MEDIUM,
                "category": "Regulatory"
            },
            {
                "text": "Are there any environmental liabilities or compliance issues?",
                "severity": SEVERITY_HIGH,
                "category": "Environmental"
            }
        ]
    },
    
    "employment_agreement": {
        "id": "employment_agreement",
        "name": "Employment Agreement Review",
        "description": "Review of executive or key employee agreements",
        "questions": [
            {
                "text": "What is the compensation structure including base salary and bonuses?",
                "severity": SEVERITY_MEDIUM,
                "category": "Compensation"
            },
            {
                "text": "Are there any equity or stock option grants?",
                "severity": SEVERITY_MEDIUM,
                "category": "Equity"
            },
            {
                "text": "What are the non-compete provisions and their duration/scope?",
                "severity": SEVERITY_HIGH,
                "category": "Non-Compete"
            },
            {
                "text": "Are there non-solicitation provisions for employees or customers?",
                "severity": SEVERITY_HIGH,
                "category": "Non-Solicitation"
            },
            {
                "text": "What are the termination provisions and severance terms?",
                "severity": SEVERITY_HIGH,
                "category": "Termination"
            },
            {
                "text": "Are there any change of control or golden parachute provisions?",
                "severity": SEVERITY_HIGH,
                "category": "Change of Control"
            },
            {
                "text": "What confidentiality or trade secret obligations exist?",
                "severity": SEVERITY_MEDIUM,
                "category": "Confidentiality"
            },
            {
                "text": "Are there any intellectual property assignment clauses?",
                "severity": SEVERITY_MEDIUM,
                "category": "IP Assignment"
            }
        ]
    }
}


def get_template(template_id: str) -> Dict[str, Any]:
    """Get an audit template by ID."""
    return AUDIT_TEMPLATES.get(template_id)


def list_templates() -> List[Dict[str, str]]:
    """List all available templates (summary only)."""
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "description": t["description"],
            "question_count": len(t["questions"])
        }
        for t in AUDIT_TEMPLATES.values()
    ]


def get_questions(template_id: str) -> List[Dict[str, Any]]:
    """Get questions for a specific template."""
    template = get_template(template_id)
    return template["questions"] if template else []
