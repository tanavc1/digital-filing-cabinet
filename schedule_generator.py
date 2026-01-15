"""
Disclosure Schedule Generator
============================

Generates disclosure schedules for M&A transactions.
These are the key deliverables that M&A attorneys produce.

Schedule Types:
1. Material Contracts - All contracts that require disclosure
2. Litigation - Pending and threatened litigation
3. IP - Intellectual property assets
4. Real Estate - Leased and owned properties
5. Employee Matters - Key employees, severance obligations
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from llm_providers import get_llm_provider, is_offline_mode

logger = logging.getLogger(__name__)


@dataclass
class ScheduleItem:
    """A single item in a disclosure schedule."""
    title: str
    category: str
    description: str
    parties: List[str]
    key_terms: str
    risk_level: str
    source_doc_id: str
    source_doc_title: str


@dataclass
class DisclosureSchedule:
    """Complete disclosure schedule."""
    schedule_type: str
    schedule_name: str
    generated_at: str
    items: List[ScheduleItem]
    summary: str
    total_count: int


SCHEDULE_TYPES = {
    "material_contracts": {
        "name": "Schedule 3.14 - Material Contracts",
        "doc_types": ["NDA / Confidentiality Agreement", "Commercial Lease", "Vendor Contract", 
                      "Software License / SaaS", "Employment Agreement"],
        "prompt": """Analyze this document and extract key contract details for a disclosure schedule.
        
Document: {title}
Content: {content}

Extract:
1. Parties to the agreement
2. Key terms (term, value, renewal, termination provisions)
3. Material obligations
4. Any change of control or assignment provisions
5. Risk factors

Respond in JSON:
{{
    "parties": ["Party A", "Party B"],
    "key_terms": "Brief summary of key terms",
    "material_obligations": "Key obligations",
    "change_of_control": "Any CoC provisions or 'None'",
    "risk_factors": "Any risk factors or 'None'",
    "risk_level": "High/Medium/Low"
}}"""
    },
    "litigation": {
        "name": "Schedule 3.10 - Litigation",
        "doc_types": ["Litigation"],
        "prompt": """Analyze this litigation document for disclosure.

Document: {title}
Content: {content}

Extract:
1. Case name and jurisdiction
2. Nature of claims
3. Current status
4. Potential exposure/damages
5. Company's position

Respond in JSON:
{{
    "case_name": "Name v. Name",
    "jurisdiction": "Court and location",
    "claims": "Nature of claims",
    "status": "Current status",
    "exposure": "Potential damages",
    "position": "Company's defense/position",
    "risk_level": "High/Medium/Low"
}}"""
    },
    "ip_assets": {
        "name": "Schedule 3.12 - Intellectual Property",
        "doc_types": ["Patent", "Trademark", "IP"],
        "prompt": """Analyze this IP document for disclosure.

Document: {title}
Content: {content}

Extract all IP assets mentioned (patents, trademarks, copyrights, trade secrets).

Respond in JSON:
{{
    "asset_type": "Patent/Trademark/Copyright/Trade Secret",
    "registration_number": "Number or 'Pending' or 'Unregistered'",
    "description": "Brief description",
    "status": "Active/Pending/Expired",
    "ownership": "Owner entity",
    "risk_level": "High/Medium/Low"
}}"""
    },
    "real_estate": {
        "name": "Schedule 3.15 - Real Estate",
        "doc_types": ["Commercial Lease", "Real Estate"],
        "prompt": """Analyze this real estate document for disclosure.

Document: {title}
Content: {content}

Extract:
1. Property address
2. Lease term and expiration
3. Monthly/annual rent
4. Assignment/subletting provisions
5. Renewal options

Respond in JSON:
{{
    "address": "Full address",
    "lease_term": "Start and end dates",
    "rent": "Monthly/annual rent amount",
    "assignment_provisions": "Assignment/subletting terms",
    "renewal_options": "Renewal terms",
    "risk_level": "High/Medium/Low"
}}"""
    },
    "employee_matters": {
        "name": "Schedule 3.16 - Employee Benefit Matters",
        "doc_types": ["Employment Agreement"],
        "prompt": """Analyze this employment document for disclosure.

Document: {title}
Content: {content}

Extract:
1. Employee name and title
2. Base compensation
3. Equity/bonus provisions
4. Severance terms
5. Change of control provisions
6. Non-compete/non-solicit terms

Respond in JSON:
{{
    "employee_name": "Name",
    "title": "Position",
    "compensation": "Base salary and bonus target",
    "equity": "Equity grants",
    "severance": "Severance terms",
    "change_of_control": "CoC acceleration or benefits",
    "restrictive_covenants": "Non-compete/non-solicit terms",
    "risk_level": "High/Medium/Low"
}}"""
    }
}


class ScheduleGenerator:
    """Generates disclosure schedules from document corpus."""
    
    def __init__(self, rag_engine):
        self.engine = rag_engine
        self.provider = get_llm_provider()
    
    async def generate_schedule(
        self,
        schedule_type: str,
        workspace_id: str,
        folder_path: Optional[str] = None
    ) -> DisclosureSchedule:
        """
        Generate a disclosure schedule of the specified type.
        
        Args:
            schedule_type: One of SCHEDULE_TYPES keys
            workspace_id: Workspace to search
            folder_path: Optional folder filter
            
        Returns:
            DisclosureSchedule with all items
        """
        if schedule_type not in SCHEDULE_TYPES:
            raise ValueError(f"Unknown schedule type: {schedule_type}")
        
        config = SCHEDULE_TYPES[schedule_type]
        logger.info(f"Generating {config['name']} for workspace {workspace_id}")
        
        # Get all documents
        docs = self.engine.store.list_documents(workspace_id)
        
        # Filter by folder if specified
        if folder_path:
            docs = [d for d in docs if d.get("folder_path", "/").startswith(folder_path)]
        
        # Filter by relevant doc types
        relevant_docs = []
        for doc in docs:
            doc_type = doc.get("doc_type", "")
            for target_type in config["doc_types"]:
                if target_type.lower() in doc_type.lower() or doc_type.lower() in target_type.lower():
                    relevant_docs.append(doc)
                    break
        
        logger.info(f"Found {len(relevant_docs)} relevant documents for {schedule_type}")
        
        # Extract schedule items from each document
        items = []
        for doc in relevant_docs:
            try:
                item = await self._extract_schedule_item(doc, config, workspace_id)
                if item:
                    items.append(item)
            except Exception as e:
                logger.warning(f"Failed to extract from {doc.get('title')}: {e}")
        
        # Generate summary
        summary = await self._generate_summary(schedule_type, items)
        
        return DisclosureSchedule(
            schedule_type=schedule_type,
            schedule_name=config["name"],
            generated_at=datetime.now().isoformat(),
            items=items,
            summary=summary,
            total_count=len(items)
        )
    
    async def _extract_schedule_item(
        self, 
        doc: Dict, 
        config: Dict,
        workspace_id: str
    ) -> Optional[ScheduleItem]:
        """Extract a schedule item from a document."""
        
        # Get document content (first few chunks)
        chunks = self.engine.store.get_chunks_by_doc_id(workspace_id, doc["doc_id"])
        if not chunks:
            return None
        
        # Combine first chunks for context (up to ~4000 chars)
        content = ""
        for chunk in sorted(chunks, key=lambda x: x.get("chunk_index", 0)):
            content += chunk.get("text", "") + "\n"
            if len(content) > 4000:
                break
        
        # Use LLM to extract structured data
        prompt = config["prompt"].format(
            title=doc.get("title", "Unknown"),
            content=content[:4000]
        )
        
        try:
            result = await self.provider.complete_json(prompt)
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            # Fallback to basic extraction
            return ScheduleItem(
                title=doc.get("title", "Unknown"),
                category=doc.get("doc_type", "Unknown"),
                description=content[:200] + "...",
                parties=[],
                key_terms="See document for details",
                risk_level=doc.get("risk_level", "Unknown"),
                source_doc_id=doc["doc_id"],
                source_doc_title=doc.get("title", "Unknown")
            )
        
        # Build schedule item from LLM response
        return ScheduleItem(
            title=doc.get("title", "Unknown"),
            category=doc.get("doc_type", "Unknown"),
            description=self._build_description(result),
            parties=result.get("parties", []),
            key_terms=result.get("key_terms", result.get("compensation", "")),
            risk_level=result.get("risk_level", doc.get("risk_level", "Unknown")),
            source_doc_id=doc["doc_id"],
            source_doc_title=doc.get("title", "Unknown")
        )
    
    def _build_description(self, result: Dict) -> str:
        """Build a description string from extraction result."""
        parts = []
        for key, value in result.items():
            if key not in ("parties", "risk_level") and value and value != "None":
                parts.append(f"{key.replace('_', ' ').title()}: {value}")
        return "; ".join(parts) if parts else "See document for details"
    
    async def _generate_summary(self, schedule_type: str, items: List[ScheduleItem]) -> str:
        """Generate an executive summary of the schedule."""
        if not items:
            return "No items found for this schedule."
        
        high_risk = [i for i in items if i.risk_level == "High"]
        
        summary_parts = [
            f"Total items: {len(items)}",
            f"High risk items: {len(high_risk)}"
        ]
        
        if high_risk:
            summary_parts.append("\nHigh Risk Items:")
            for item in high_risk[:5]:  # Top 5
                summary_parts.append(f"  - {item.title}: {item.key_terms[:100]}")
        
        return "\n".join(summary_parts)
    
    def list_schedule_types(self) -> List[Dict[str, str]]:
        """List available schedule types."""
        return [
            {"id": k, "name": v["name"]}
            for k, v in SCHEDULE_TYPES.items()
        ]
