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
    },
    
    "nda_review": {
        "id": "nda_review",
        "name": "NDA / Confidentiality Review",
        "description": "Review of Non-Disclosure and confidentiality agreements",
        "questions": [
            {
                "text": "What is the definition of Confidential Information and what exclusions exist?",
                "severity": SEVERITY_HIGH,
                "category": "Definitions"
            },
            {
                "text": "What is the term of the confidentiality obligations?",
                "severity": SEVERITY_HIGH,
                "category": "Term"
            },
            {
                "text": "Are there any carve-outs for legally required disclosures?",
                "severity": SEVERITY_MEDIUM,
                "category": "Permitted Disclosures"
            },
            {
                "text": "What are the return or destruction obligations for confidential materials?",
                "severity": SEVERITY_MEDIUM,
                "category": "Return of Materials"
            },
            {
                "text": "Is there an injunctive relief or specific performance clause?",
                "severity": SEVERITY_MEDIUM,
                "category": "Remedies"
            },
            {
                "text": "Does the NDA include non-solicitation provisions?",
                "severity": SEVERITY_HIGH,
                "category": "Non-Solicitation"
            },
            {
                "text": "What law governs and what is the dispute resolution mechanism?",
                "severity": SEVERITY_LOW,
                "category": "Governing Law"
            }
        ]
    },
    
    "general_contract": {
        "id": "general_contract",
        "name": "General Contract Review",
        "description": "Standard contract review checklist for any agreement",
        "questions": [
            {
                "text": "Who are the parties to this agreement and are they correctly identified?",
                "severity": SEVERITY_LOW,
                "category": "Parties"
            },
            {
                "text": "What are the key obligations of each party?",
                "severity": SEVERITY_HIGH,
                "category": "Obligations"
            },
            {
                "text": "What is the term of the agreement and are there renewal provisions?",
                "severity": SEVERITY_MEDIUM,
                "category": "Term"
            },
            {
                "text": "What are the payment terms and amounts?",
                "severity": SEVERITY_HIGH,
                "category": "Payment"
            },
            {
                "text": "Are there any indemnification obligations and what are the caps?",
                "severity": SEVERITY_HIGH,
                "category": "Indemnification"
            },
            {
                "text": "What are the limitation of liability provisions?",
                "severity": SEVERITY_HIGH,
                "category": "Liability"
            },
            {
                "text": "Are there any warranty or representation provisions?",
                "severity": SEVERITY_MEDIUM,
                "category": "Warranties"
            },
            {
                "text": "What events allow termination and what is the required notice period?",
                "severity": SEVERITY_HIGH,
                "category": "Termination"
            },
            {
                "text": "What provisions survive termination of the agreement?",
                "severity": SEVERITY_MEDIUM,
                "category": "Survival"
            },
            {
                "text": "What is the governing law and dispute resolution mechanism?",
                "severity": SEVERITY_LOW,
                "category": "Governing Law"
            },
            {
                "text": "Are there any assignment restrictions?",
                "severity": SEVERITY_MEDIUM,
                "category": "Assignment"
            },
            {
                "text": "Is there a force majeure clause and what does it cover?",
                "severity": SEVERITY_LOW,
                "category": "Force Majeure"
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


# ----------------------------
# Custom Template Storage
# ----------------------------
import json
import os

CUSTOM_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "data", "custom_templates")


def _ensure_custom_dir():
    """Ensure the custom templates directory exists."""
    os.makedirs(CUSTOM_TEMPLATES_DIR, exist_ok=True)


def save_custom_template(template: Dict[str, Any]) -> str:
    """
    Save a custom audit template.
    
    Args:
        template: Template dict with 'id', 'name', 'description', 'questions'
        
    Returns:
        The template ID
    """
    _ensure_custom_dir()
    
    template_id = template.get("id")
    if not template_id:
        import uuid
        template_id = f"custom_{uuid.uuid4().hex[:8]}"
        template["id"] = template_id
    
    # Validate structure
    if "name" not in template:
        template["name"] = f"Custom Template {template_id}"
    if "description" not in template:
        template["description"] = "User-created audit template"
    if "questions" not in template:
        template["questions"] = []
    
    # Ensure questions have required fields
    for i, q in enumerate(template["questions"]):
        if isinstance(q, str):
            template["questions"][i] = {
                "text": q,
                "severity": SEVERITY_MEDIUM,
                "category": "Custom"
            }
        elif isinstance(q, dict):
            if "text" not in q:
                continue
            if "severity" not in q:
                q["severity"] = SEVERITY_MEDIUM
            if "category" not in q:
                q["category"] = "Custom"
    
    # Mark as custom
    template["is_custom"] = True
    
    # Save to file
    filepath = os.path.join(CUSTOM_TEMPLATES_DIR, f"{template_id}.json")
    with open(filepath, "w") as f:
        json.dump(template, f, indent=2)
    
    return template_id


def load_custom_template(template_id: str) -> Dict[str, Any]:
    """Load a custom template by ID."""
    _ensure_custom_dir()
    filepath = os.path.join(CUSTOM_TEMPLATES_DIR, f"{template_id}.json")
    
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, "r") as f:
        return json.load(f)


def list_custom_templates() -> List[Dict[str, Any]]:
    """List all custom templates (summary only)."""
    _ensure_custom_dir()
    templates = []
    
    for filename in os.listdir(CUSTOM_TEMPLATES_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(CUSTOM_TEMPLATES_DIR, filename)
            try:
                with open(filepath, "r") as f:
                    t = json.load(f)
                    templates.append({
                        "id": t.get("id"),
                        "name": t.get("name"),
                        "description": t.get("description"),
                        "question_count": len(t.get("questions", [])),
                        "is_custom": True
                    })
            except Exception:
                continue
    
    return templates


def delete_custom_template(template_id: str) -> bool:
    """Delete a custom template."""
    _ensure_custom_dir()
    filepath = os.path.join(CUSTOM_TEMPLATES_DIR, f"{template_id}.json")
    
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def get_all_templates() -> List[Dict[str, Any]]:
    """Get all templates (predefined + custom)."""
    all_templates = list_templates()  # Predefined
    all_templates.extend(list_custom_templates())  # Custom
    return all_templates


def get_template_unified(template_id: str) -> Dict[str, Any]:
    """Get a template by ID (checks predefined first, then custom)."""
    # Check predefined
    template = get_template(template_id)
    if template:
        return template
    
    # Check custom
    return load_custom_template(template_id)
