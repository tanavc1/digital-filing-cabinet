"""
Playbook Engine
===============

LLM-powered clause extraction engine for M&A due diligence.
Runs playbooks against documents to extract key clause information.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from models.clause import (
    ClauseExtraction, 
    ClauseType, 
    Playbook, 
    PLAYBOOKS, 
    get_playbook,
    CLAUSE_LABELS
)
from models.issue import Issue, IssueSeverity
from llm_providers import get_llm_provider

logger = logging.getLogger(__name__)


# Clause extraction prompts for each type - STRICT and SPECIFIC
CLAUSE_PROMPTS = {
    ClauseType.ASSIGNMENT_CONSENT: """
FIND ONLY: Assignment or transfer provisions - who can assign this contract and what consent is needed.

LOOK FOR THESE EXACT KEYWORDS: "assign", "transfer", "assignable", "consent", "novation"

DO NOT EXTRACT: Termination clauses, renewal terms, liability caps, or any other clause type.

EXAMPLE GOOD ANSWERS:
- "May not assign without prior written consent"
- "Freely assignable to affiliates"
- "Assignment requires 30 days notice"

If no assignment/consent language exists, set found=false.
""",
    ClauseType.CHANGE_OF_CONTROL: """
FIND ONLY: What happens when company ownership changes (merger, acquisition, sale of majority stake).

LOOK FOR THESE EXACT KEYWORDS: "change of control", "change in ownership", "merger", "acquisition", "majority"

DO NOT EXTRACT: Termination clauses (unless specifically triggered by change of control), assignment clauses.

EXAMPLE GOOD ANSWERS:
- "Either party may terminate upon change of control"
- "Change of control requires 60 days notice"
- "Agreement continues through change of control"

If no change of control language exists, set found=false.
""",
    ClauseType.TERM_RENEWAL: """
FIND ONLY: How long is the initial contract term, and how does it renew?

LOOK FOR THESE EXACT KEYWORDS: "term", "initial term", "renewal", "renew", "auto-renew", "evergreen", "period of"

DO NOT EXTRACT: Termination notice periods, assignment provisions.

EXAMPLE GOOD ANSWERS:
- "Initial term: 3 years, auto-renews annually"
- "Term of 24 months with two 1-year renewals"
- "Evergreen agreement with 90 day opt-out"

If no term/renewal language exists, set found=false.
""",
    ClauseType.TERMINATION_NOTICE: """
FIND ONLY: How can this contract be terminated and what notice is required?

LOOK FOR THESE EXACT KEYWORDS: "terminate", "termination", "cancel", "notice", "days notice", "for cause", "for convenience"

DO NOT EXTRACT: Term/renewal provisions, assignment provisions.

EXAMPLE GOOD ANSWERS:
- "Either party may terminate with 30 days written notice"
- "Termination for cause: immediate upon material breach"
- "90 days notice required for termination"

If no termination language exists, set found=false.
""",
    ClauseType.LIABILITY_CAP: """
FIND ONLY: Maximum liability amounts or limitations on damages.

LOOK FOR THESE EXACT KEYWORDS: "liability", "limitation of liability", "cap", "maximum", "aggregate", "shall not exceed", "damages"

DO NOT EXTRACT: Indemnification provisions, insurance requirements.

EXAMPLE GOOD ANSWERS:
- "Liability capped at 12 months of fees paid"
- "Maximum aggregate liability: $1,000,000"
- "No liability cap for gross negligence"

If no liability cap language exists, set found=false.
""",
    ClauseType.GOVERNING_LAW: """
FIND ONLY: Which state/country's laws govern this contract?

LOOK FOR THESE EXACT KEYWORDS: "governing law", "governed by", "laws of", "jurisdiction", "venue"

DO NOT EXTRACT: Dispute resolution, arbitration clauses (unless they specify jurisdiction).

EXAMPLE GOOD ANSWERS:
- "Governed by the laws of Delaware"
- "Jurisdiction: State of California"
- "Laws of the State of New York"

If no governing law language exists, set found=false.
""",
    ClauseType.MFN_EXCLUSIVITY: """
FIND ONLY: Most favored nation pricing or exclusivity arrangements.

LOOK FOR THESE EXACT KEYWORDS: "most favored", "MFN", "exclusive", "exclusivity", "sole provider", "sole supplier"

DO NOT EXTRACT: Standard pricing terms, non-compete clauses.

EXAMPLE GOOD ANSWERS:
- "Exclusive supplier for North America"
- "Most favored nation pricing applies"
- "Non-exclusive arrangement"

If no MFN/exclusivity language exists, set found=false.
""",
    ClauseType.SEVERANCE: """
FIND ONLY: Severance or separation payments to employees upon termination.

LOOK FOR THESE EXACT KEYWORDS: "severance", "separation", "termination payment", "months salary", "separation agreement"

DO NOT EXTRACT: Contract termination provisions (this is about EMPLOYEE severance only).

EXAMPLE GOOD ANSWERS:
- "12 months base salary upon termination"
- "Severance: 2 weeks per year of service"
- "Accelerated vesting upon separation"

If no severance language exists, set found=false.
""",
    ClauseType.NON_COMPETE: """
FIND ONLY: Restrictions on competing or soliciting employees/customers.

LOOK FOR THESE EXACT KEYWORDS: "non-compete", "non-solicitation", "shall not compete", "restrictive covenant", "compete with"

DO NOT EXTRACT: Confidentiality provisions, IP restrictions.

EXAMPLE GOOD ANSWERS:
- "2-year non-compete within 50 miles"
- "Non-solicitation of employees for 1 year"
- "No non-compete restrictions"

If no non-compete language exists, set found=false.
""",
    ClauseType.IP_LICENSE: """
FIND ONLY: Intellectual property license grants and restrictions.

LOOK FOR THESE EXACT KEYWORDS: "license", "IP", "intellectual property", "perpetual", "royalty", "grant"

DO NOT EXTRACT: General service descriptions, SLA terms.

EXAMPLE GOOD ANSWERS:
- "Perpetual, non-exclusive license"
- "Royalty-free license to use"
- "IP remains with Provider"

If no IP license language exists, set found=false.
""",
}

# Required keywords for validation - extraction must contain at least one of these
CLAUSE_KEYWORDS = {
    ClauseType.ASSIGNMENT_CONSENT: ["assign", "transfer", "assignable", "consent", "novation"],
    ClauseType.CHANGE_OF_CONTROL: ["change of control", "change in ownership", "merger", "acquisition", "majority stake"],
    ClauseType.TERM_RENEWAL: ["initial term", "renewal", "renew", "auto-renew", "evergreen", "term of"],
    ClauseType.TERMINATION_NOTICE: ["terminate", "termination", "cancel", "days notice", "for cause", "for convenience"],
    ClauseType.LIABILITY_CAP: ["liability", "limitation of liability", "cap", "maximum liability", "aggregate", "shall not exceed", "damages"],
    ClauseType.GOVERNING_LAW: ["governing law", "governed by", "laws of the state", "jurisdiction", "venue"],
    ClauseType.MFN_EXCLUSIVITY: ["most favored", "mfn", "exclusive", "exclusivity", "sole provider"],
    ClauseType.SEVERANCE: ["severance", "separation pay", "termination payment", "months salary"],
    ClauseType.NON_COMPETE: ["non-compete", "non-solicitation", "shall not compete", "restrictive covenant", "compete with"],
    ClauseType.IP_LICENSE: ["license grant", "intellectual property", "perpetual license", "royalty", "ip rights"],
}

def count_keyword_matches(clause_type: ClauseType, text: str) -> int:
    """Count how many keywords from a clause type appear in the text."""
    text_lower = text.lower()
    keywords = CLAUSE_KEYWORDS.get(clause_type, [])
    return sum(1 for kw in keywords if kw.lower() in text_lower)

def detect_cross_contamination(requested_type: ClauseType, text: str) -> Optional[ClauseType]:
    """
    Check if the text matches a DIFFERENT clause type better than the requested one.
    Returns the wrong clause type if cross-contamination detected, None otherwise.
    """
    text_lower = text.lower()
    requested_matches = count_keyword_matches(requested_type, text)
    
    # Check all other clause types
    for other_type, keywords in CLAUSE_KEYWORDS.items():
        if other_type == requested_type:
            continue
        other_matches = count_keyword_matches(other_type, text)
        
        # If another type has MORE matches than the requested type, it's cross-contamination
        if other_matches > requested_matches and other_matches >= 2:
            return other_type
    
    return None

def calculate_confidence(clause_type: ClauseType, text: str, has_snippet: bool) -> float:
    """
    Calculate confidence score based on keyword matches and cross-contamination.
    Returns a score between 0.0 and 1.0
    """
    base_confidence = 0.7 if has_snippet else 0.4
    
    # Boost for keyword matches
    matches = count_keyword_matches(clause_type, text)
    if matches >= 3:
        base_confidence += 0.25
    elif matches >= 2:
        base_confidence += 0.15
    elif matches >= 1:
        base_confidence += 0.05
    else:
        base_confidence -= 0.2  # Penalize no keyword matches
    
    # Penalize for cross-contamination
    wrong_type = detect_cross_contamination(clause_type, text)
    if wrong_type:
        base_confidence -= 0.4
    
    return max(0.1, min(1.0, base_confidence))


class PlaybookEngine:
    """Engine for running playbooks against documents."""
    
    def __init__(self, rag_engine):
        """
        Initialize with a RAG engine for document access.
        
        Args:
            rag_engine: RAGEngine instance for accessing documents
        """
        self.engine = rag_engine
        self.provider = get_llm_provider()
    
    def list_playbooks(self) -> List[Dict]:
        """List all available playbooks."""
        return [pb.to_dict() for pb in PLAYBOOKS]
    
    async def run_playbook(
        self, 
        playbook_id: str, 
        workspace_id: str,
        doc_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run a playbook against documents.
        
        Args:
            playbook_id: ID of playbook to run
            workspace_id: Workspace containing documents
            doc_ids: Optional specific doc IDs, otherwise uses all matching types
            
        Returns:
            Dict with extractions and any issues found
        """
        playbook = get_playbook(playbook_id)
        if not playbook:
            raise ValueError(f"Unknown playbook: {playbook_id}")
        
        logger.info(f"Running playbook '{playbook.name}' on workspace {workspace_id}")
        
        # Get documents
        all_docs = self.engine.store.list_documents(workspace_id)
        
        # Filter by doc type if not specific IDs given
        if doc_ids:
            docs = [d for d in all_docs if d["doc_id"] in doc_ids]
        else:
            docs = []
            logger.info(f"Filtering {len(all_docs)} docs for playbook {playbook.name} (Targets: {playbook.doc_types})")
            for doc in all_docs:
                doc_type = doc.get("doc_type", "")
                logger.info(f"  - Checking '{doc.get('title')}' (Type: '{doc_type}')")
                for target_type in playbook.doc_types:
                    if target_type.lower() in doc_type.lower() or doc_type.lower() in target_type.lower():
                        docs.append(doc)
                        break
        
        logger.info(f"Selected {len(docs)} documents for playbook execution")
        
        # LIMIT: Process at most 3 documents per run for Ollama compatibility
        MAX_DOCS_PER_RUN = 3
        if len(docs) > MAX_DOCS_PER_RUN:
            logger.warning(f"Limiting playbook to first {MAX_DOCS_PER_RUN} of {len(docs)} documents")
            docs = docs[:MAX_DOCS_PER_RUN]
        
        # LIMIT: Process at most 4 clause types for faster execution
        MAX_CLAUSE_TYPES = 4
        clause_types_to_use = playbook.clause_types[:MAX_CLAUSE_TYPES]
        logger.info(f"Processing {len(docs)} documents with {len(clause_types_to_use)} clause types")
        
        # Extract clauses from each document
        all_extractions = []
        all_issues = []
        
        for doc in docs:
            try:
                extractions, issues = await self._extract_clauses_from_doc(
                    doc, 
                    clause_types_to_use,
                    workspace_id
                )
                all_extractions.extend(extractions)
                all_issues.extend(issues)
            except Exception as e:
                logger.error(f"Failed to extract from {doc.get('title')}: {e}")
        
        return {
            "playbook_id": playbook_id,
            "playbook_name": playbook.name,
            "doc_count": len(docs),
            "extraction_count": len(all_extractions),
            "issue_count": len(all_issues),
            "extractions": [e.to_dict() for e in all_extractions],
            "issues": [i.to_dict() for i in all_issues],
        }
    
    async def _extract_clauses_from_doc(
        self,
        doc: Dict,
        clause_types: List[ClauseType],
        workspace_id: str
    ) -> tuple[List[ClauseExtraction], List[Issue]]:
        """Extract specified clause types from a single document."""
        
        # Get document content
        chunks = self.engine.store.get_chunks_by_doc_id(workspace_id, doc["doc_id"])
        if not chunks:
            return [], []
        
        # Combine chunks for context
        content = ""
        for chunk in sorted(chunks, key=lambda x: x.get("chunk_index", 0)):
            content += chunk.get("text", "") + "\n\n"
            if len(content) > 8000:  # Limit context
                break
        
        extractions = []
        issues = []
        
        # Extract each clause type
        for clause_type in clause_types:
            try:
                extraction, issue = await self._extract_single_clause(
                    doc, content, clause_type
                )
                if extraction:
                    extractions.append(extraction)
                if issue:
                    issues.append(issue)
            except Exception as e:
                logger.warning(f"Failed to extract {clause_type.value} from {doc.get('title')}: {e}")
        
        return extractions, issues
    
    async def _extract_single_clause(
        self,
        doc: Dict,
        content: str,
        clause_type: ClauseType
    ) -> tuple[Optional[ClauseExtraction], Optional[Issue]]:
        """Extract a single clause type from document content."""
        
        prompt = f"""You are a legal document analyst. Your task is to find ONE SPECIFIC clause type in a document.

CRITICAL RULES:
1. ONLY extract information about the EXACT clause type requested below
2. If you find related but different clause types, IGNORE THEM
3. If the exact clause type is not present, set found=false
4. The snippet must contain keywords specific to the clause type

DOCUMENT: {doc.get('title', 'Unknown')}

═══════════════════════════════════════════════════════
CLAUSE TYPE TO EXTRACT: {CLAUSE_LABELS.get(clause_type, clause_type.value)}
═══════════════════════════════════════════════════════

{CLAUSE_PROMPTS.get(clause_type, 'Extract relevant information.')}

DOCUMENT CONTENT:
{content[:6000]}

Respond in JSON format:
{{
    "found": true/false,
    "extracted_value": "Brief summary ONLY for {CLAUSE_LABELS.get(clause_type, clause_type.value)} (not other clauses)",
    "snippet": "Exact quote containing {CLAUSE_LABELS.get(clause_type, clause_type.value).lower()} language (max 200 chars)",
    "risk_level": "high/medium/low/none",
    "risk_reason": "Why this specific clause is a risk (if any)"
}}

REMEMBER: If this specific clause type ({CLAUSE_LABELS.get(clause_type, clause_type.value)}) is not in the document, set found=false. Do NOT return other clause types.
"""
        
        try:
            result = await self.provider.complete_json(prompt)
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            return None, None
        
        if not result.get("found", False):
            return None, None
        
        # Get extraction text for analysis
        snippet = result.get("snippet", "")
        extracted_value = result.get("extracted_value", "")
        combined_text = f"{snippet} {extracted_value}"
        
        # STEP 1: Check for cross-contamination (text matches wrong clause type better)
        wrong_type = detect_cross_contamination(clause_type, combined_text)
        if wrong_type:
            logger.warning(f"Cross-contamination detected: Asked for {clause_type.value}, "
                          f"but text matches {wrong_type.value} better. Snippet: '{snippet[:50]}...'")
            return None, None
        
        # STEP 2: Two-pass verification for low-confidence extractions
        keyword_matches = count_keyword_matches(clause_type, combined_text)
        if keyword_matches == 0:
            # No keywords found - ask LLM to verify this is really the right clause type
            verify_prompt = f"""Is this text SPECIFICALLY about {CLAUSE_LABELS.get(clause_type, clause_type.value)}?

TEXT: "{snippet}"

Answer with ONLY "yes" or "no". If the text is about a DIFFERENT clause type (like termination, assignment, liability, etc.), answer "no"."""
            
            try:
                verify_result = await self.provider.complete(verify_prompt)
                if "no" in verify_result.lower()[:10]:
                    logger.warning(f"Two-pass verification rejected {clause_type.value}: '{snippet[:50]}...'")
                    return None, None
            except Exception as e:
                logger.warning(f"Verification failed, rejecting uncertain extraction: {e}")
                return None, None
        
        # STEP 3: Calculate confidence based on keyword analysis
        has_snippet = bool(snippet)
        confidence = calculate_confidence(clause_type, combined_text, has_snippet)
        
        # Create extraction with calculated confidence
        extraction = ClauseExtraction(
            doc_id=doc["doc_id"],
            doc_title=doc.get("title", "Unknown"),
            clause_type=clause_type,
            extracted_value=result.get("extracted_value", ""),
            snippet=result.get("snippet", "")[:500],
            page_number=1,  # TODO: Extract actual page
            confidence=confidence,
            verified=False,
            flagged=result.get("risk_level") == "high",
        )
        
        # Create issue if high risk
        issue = None
        if result.get("risk_level") == "high":
            issue = Issue(
                title=f"{CLAUSE_LABELS.get(clause_type, clause_type.value)} - {doc.get('title', 'Unknown')}",
                description=result.get("risk_reason", "High risk clause detected"),
                severity=IssueSeverity.CRITICAL,
                doc_id=doc["doc_id"],
                doc_title=doc.get("title"),
                clause_id=extraction.id,
                action_required="Review and assess impact on transaction",
            )
        elif result.get("risk_level") == "medium":
            issue = Issue(
                title=f"{CLAUSE_LABELS.get(clause_type, clause_type.value)} - {doc.get('title', 'Unknown')}",
                description=result.get("risk_reason", "Medium risk clause detected"),
                severity=IssueSeverity.WARNING,
                doc_id=doc["doc_id"],
                doc_title=doc.get("title"),
                clause_id=extraction.id,
                action_required="Review during diligence",
            )
        
        return extraction, issue
    
    def build_matrix(self, extractions: List[ClauseExtraction]) -> Dict[str, Any]:
        """
        Build a clause matrix from extractions.
        
        Returns matrix where rows are documents and columns are clause types.
        """
        # Group by document
        by_doc = {}
        for e in extractions:
            if e.doc_id not in by_doc:
                by_doc[e.doc_id] = {
                    "doc_id": e.doc_id,
                    "doc_title": e.doc_title,
                    "clauses": {}
                }
            by_doc[e.doc_id]["clauses"][e.clause_type.value] = {
                "id": e.id,
                "value": e.extracted_value,
                "snippet": e.snippet,
                "confidence": e.confidence,
                "verified": e.verified,
                "flagged": e.flagged,
            }
        
        # Get all clause types present
        all_types = set()
        for doc_data in by_doc.values():
            all_types.update(doc_data["clauses"].keys())
        
        return {
            "columns": sorted(list(all_types)),
            "column_labels": {ct: CLAUSE_LABELS.get(ClauseType(ct), ct) for ct in all_types},
            "rows": list(by_doc.values()),
        }
