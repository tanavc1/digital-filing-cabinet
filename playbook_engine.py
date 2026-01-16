"""
Playbook Engine
===============

LLM-powered clause extraction engine for M&A due diligence.
Runs playbooks against documents to extract key clause information.
"""

import logging
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

from models.clause import (
    ClauseExtraction, 
    ClauseType, 
    Playbook, 
    PLAYBOOKS, 
    get_playbook,
    CLAUSE_LABELS,
    Evidence,
    ExtractionStatus
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
        
        # If specific doc_ids given, filter to those
        if doc_ids:
            docs_to_process = [d for d in all_docs if d["doc_id"] in doc_ids]
        else:
            docs_to_process = all_docs
        
        logger.info(f"Processing {len(docs_to_process)} documents for playbook {playbook.name}")
        
        clause_types_to_use = playbook.clause_types
        logger.info(f"Processing {len(docs_to_process)} documents with {len(clause_types_to_use)} clause types")
        
        # Extract clauses from each document
        all_extractions = []
        all_issues = []
        matching_doc_count = 0
        
        for doc in docs_to_process:
            doc_type = doc.get("doc_type", "")
            
            # Check if doc type matches playbook targets
            is_matching = False
            for target_type in playbook.doc_types:
                if target_type.lower() in doc_type.lower() or doc_type.lower() in target_type.lower():
                    is_matching = True
                    break
            
            if is_matching:
                # Matching doc type → extract clauses normally
                matching_doc_count += 1
                logger.info(f"  ✓ '{doc.get('title')}' (Type: '{doc_type}') - EXTRACTING")
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
            else:
                # Non-matching doc type → create NOT_APPLICABLE extractions
                logger.info(f"  ✗ '{doc.get('title')}' (Type: '{doc_type}') - NOT_APPLICABLE")
                for clause_type in clause_types_to_use:
                    extraction = ClauseExtraction(
                        doc_id=doc["doc_id"],
                        doc_title=doc.get("title", "Unknown"),
                        clause_type=clause_type,
                        extracted_value="",
                        status=ExtractionStatus.NOT_APPLICABLE,
                        evidence=[],
                        explanation=f"Document type '{doc_type}' not in playbook targets: {playbook.doc_types}",
                        snippet="",
                        page_number=1,
                        confidence=0.0,
                        verified=False,
                        flagged=False,
                    )
                    all_extractions.append(extraction)
        
        return {
            "playbook_id": playbook_id,
            "playbook_name": playbook.name,
            "doc_count": len(docs_to_process),
            "matching_doc_count": matching_doc_count,
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
        """
        Extract specified clause types from a single document.
        
        OPTIMIZATION: Uses a single batched LLM call to extract ALL clause types
        at once instead of 7 separate calls. This reduces LLM roundtrips by 7x.
        """
        
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
        
        # Build batched extraction prompt for ALL clause types at once
        clause_list = [f"- {CLAUSE_LABELS.get(ct, ct.value)} ({ct.value})" for ct in clause_types]
        clause_list_str = "\n".join(clause_list)
        
        batch_prompt = f"""You are a legal document analyst. Extract ALL of the following clause types from this document IN A SINGLE RESPONSE.

DOCUMENT: {doc.get('title', 'Unknown')}

═══════════════════════════════════════════════════════
CLAUSE TYPES TO EXTRACT:
{clause_list_str}
═══════════════════════════════════════════════════════

DOCUMENT CONTENT:
{content[:6000]}

For EACH clause type listed above, provide a JSON object with these fields:
- clause_type: the exact clause type key (e.g. "assignment_consent")
- found: true/false
- page_number: integer from nearest '## Page X' marker
- extracted_value: brief normalized summary (e.g. 'Consent required', '12 months notice')
- snippet: exact quote from document (max 200 chars)
- char_start: approximate character position where snippet begins
- risk_level: "high"/"medium"/"low"/"none"
- risk_reason: why this is a risk (if any)
- explanation: brief reason for finding

Respond with a JSON object containing an array called "clauses":
{{
    "clauses": [
        {{"clause_type": "assignment_consent", "found": true/false, ...}},
        {{"clause_type": "change_of_control", "found": true/false, ...}},
        ... (one entry for each clause type listed above)
    ]
}}

IMPORTANT: Include an entry for EVERY clause type listed, even if not found (set found=false).
"""
        
        extractions = []
        issues = []
        
        try:
            result = await self.provider.complete_json(batch_prompt)
            clauses_data = result.get("clauses", [])
            
            # Build a lookup for easy access
            clause_results = {c.get("clause_type"): c for c in clauses_data}
            
            # Process each clause type
            for clause_type in clause_types:
                clause_data = clause_results.get(clause_type.value, {})
                extraction, issue = self._process_clause_result(doc, content, clause_type, clause_data)
                if extraction:
                    extractions.append(extraction)
                if issue:
                    issues.append(issue)
                    
        except Exception as e:
            logger.warning(f"Batch extraction failed for {doc.get('title')}: {e}")
            # Fallback: return UNRESOLVED for all clause types
            for clause_type in clause_types:
                extractions.append(ClauseExtraction(
                    doc_id=doc["doc_id"],
                    doc_title=doc.get("title", "Unknown"),
                    clause_type=clause_type,
                    extracted_value="",
                    status=ExtractionStatus.UNRESOLVED,
                    evidence=[],
                    explanation=f"Batch extraction failed: {str(e)[:100]}",
                    snippet="",
                    page_number=1,
                    confidence=0.0,
                    verified=False,
                    flagged=False,
                ))
        
        return extractions, issues
    
    def _process_clause_result(
        self,
        doc: Dict,
        content: str,
        clause_type: ClauseType,
        result: Dict
    ) -> tuple[Optional[ClauseExtraction], Optional[Issue]]:
        """Process a single clause extraction result from batch response."""
        
        if not result or not result.get("found", False):
            # Clause not found → UNRESOLVED
            return ClauseExtraction(
                doc_id=doc["doc_id"],
                doc_title=doc.get("title", "Unknown"),
                clause_type=clause_type,
                extracted_value="",
                status=ExtractionStatus.UNRESOLVED,
                evidence=[],
                explanation=result.get("explanation", f"No {CLAUSE_LABELS.get(clause_type, clause_type.value).lower()} language found"),
                snippet="",
                page_number=1,
                confidence=0.0,
                verified=False,
                flagged=False,
            ), None
        
        # Found clause - process it
        snippet = result.get("snippet", "")[:500]
        extracted_value = result.get("extracted_value", "")
        page_number = result.get("page_number", 1)
        
        # Calculate confidence
        confidence = calculate_confidence(snippet, clause_type, extracted_value)
        
        # Check for cross-contamination
        contamination = detect_cross_contamination(snippet, clause_type)
        if contamination:
            return ClauseExtraction(
                doc_id=doc["doc_id"],
                doc_title=doc.get("title", "Unknown"),
                clause_type=clause_type,
                extracted_value="",
                status=ExtractionStatus.UNRESOLVED,
                evidence=[],
                explanation=f"Cross-contamination detected: {contamination}",
                snippet="",
                page_number=1,
                confidence=0.0,
                verified=False,
                flagged=False,
            ), None
        
        # Build evidence
        char_start = result.get("char_start", 0)
        char_end = char_start + len(snippet)
        evidence_list = []
        if snippet:
            evidence_list.append(Evidence(
                file=doc.get("title", "Unknown"),
                page=page_number,
                snippet=snippet,
                char_start=char_start,
                char_end=char_end,
            ))
        
        # Determine status based on confidence
        if evidence_list and confidence >= 0.8:
            status = ExtractionStatus.RESOLVED
        elif evidence_list:
            status = ExtractionStatus.NEEDS_REVIEW
        else:
            status = ExtractionStatus.UNRESOLVED
        
        extraction = ClauseExtraction(
            doc_id=doc["doc_id"],
            doc_title=doc.get("title", "Unknown"),
            clause_type=clause_type,
            extracted_value=extracted_value,
            status=status,
            evidence=evidence_list,
            explanation=result.get("explanation", f"Extracted with {confidence:.0%} confidence"),
            snippet=snippet,
            page_number=page_number,
            confidence=confidence,
            verified=False,
            flagged=result.get("risk_level") == "high",
        )
        
        # Create issue if high/medium risk
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
    
    async def _extract_single_clause(
        self,
        doc: Dict,
        content: str,
        clause_type: ClauseType
    ) -> tuple[Optional[ClauseExtraction], Optional[Issue]]:
        """
        Extract a single clause type from document content with evidence-gated logic.
        
        HARD RULE: Every clause is either:
        - RESOLVED (has evidence + confidence >= 0.8)
        - NEEDS_REVIEW (has evidence but low confidence)  
        - UNRESOLVED (no evidence found - never blank)
        """
        
        prompt = f"""You are a legal document analyst. Your task is to find ONE SPECIFIC clause type in a document.

CRITICAL RULES:
1. ONLY extract information about the EXACT clause type requested below
2. If you find related but different clause types, IGNORE THEM
3. If the exact clause type is not present, set found=false
4. The snippet must contain keywords specific to the clause type
5. Look for "## Page X" markers in the content. The page_number is the number in the marker IMMEDIATELY PRECEDING the snippet.
6. IMPORTANT: Provide the exact character position where the snippet starts in the document.

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
    "page_number": <Integer from the nearest '## Page X' marker above the snippet>, 
    "extracted_value": "Brief normalized summary (e.g. 'Consent required', '12 months notice')",
    "snippet": "Exact quote from document (max 200 chars)",
    "char_start": <approximate character position where snippet begins>,
    "risk_level": "high/medium/low/none",
    "risk_reason": "Why this specific clause is a risk (if any)",
    "explanation": "Brief reason for this finding"
}}

REMEMBER: If this specific clause type ({CLAUSE_LABELS.get(clause_type, clause_type.value)}) is not in the document, set found=false and provide explanation="No {CLAUSE_LABELS.get(clause_type, clause_type.value).lower()} language found in document".
"""
        
        try:
            result = await self.provider.complete_json(prompt)
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            # Return UNRESOLVED extraction on LLM failure
            return ClauseExtraction(
                doc_id=doc["doc_id"],
                doc_title=doc.get("title", "Unknown"),
                clause_type=clause_type,
                extracted_value="",
                status=ExtractionStatus.UNRESOLVED,
                evidence=[],
                explanation=f"Extraction failed: {str(e)[:100]}",
                snippet="",
                page_number=1,
                confidence=0.0,
                verified=False,
                flagged=False,
            ), None
        
        # CASE 1: Clause not found → return UNRESOLVED (never blank)
        if not result.get("found", False):
            return ClauseExtraction(
                doc_id=doc["doc_id"],
                doc_title=doc.get("title", "Unknown"),
                clause_type=clause_type,
                extracted_value="",
                status=ExtractionStatus.UNRESOLVED,
                evidence=[],
                explanation=result.get("explanation", f"No {CLAUSE_LABELS.get(clause_type, clause_type.value).lower()} found"),
                snippet="",
                page_number=1,
                confidence=0.0,
                verified=False,
                flagged=False,
            ), None
        
        # Get extraction text for analysis
        snippet = result.get("snippet", "")
        extracted_value = result.get("extracted_value", "")
        combined_text = f"{snippet} {extracted_value}"
        
        # STEP 1: Check for cross-contamination (text matches wrong clause type better)
        wrong_type = detect_cross_contamination(clause_type, combined_text)
        if wrong_type:
            logger.warning(f"Cross-contamination detected: Asked for {clause_type.value}, "
                          f"but text matches {wrong_type.value} better. Snippet: '{snippet[:50]}...'")
            return ClauseExtraction(
                doc_id=doc["doc_id"],
                doc_title=doc.get("title", "Unknown"),
                clause_type=clause_type,
                extracted_value="",
                status=ExtractionStatus.UNRESOLVED,
                evidence=[],
                explanation=f"Cross-contamination: extracted text matches {wrong_type.value} better",
                snippet="",
                page_number=1,
                confidence=0.0,
                verified=False,
                flagged=False,
            ), None
        
        # STEP 2: Two-pass verification for low-confidence extractions
        keyword_matches = count_keyword_matches(clause_type, combined_text)
        if keyword_matches == 0:
            verify_prompt = f"""Is this text SPECIFICALLY about {CLAUSE_LABELS.get(clause_type, clause_type.value)}?

TEXT: "{snippet}"

Answer with ONLY "yes" or "no". If the text is about a DIFFERENT clause type (like termination, assignment, liability, etc.), answer "no"."""
            
            try:
                verify_result = await self.provider.complete(verify_prompt)
                if "no" in verify_result.lower()[:10]:
                    logger.warning(f"Two-pass verification rejected {clause_type.value}: '{snippet[:50]}...'")
                    return ClauseExtraction(
                        doc_id=doc["doc_id"],
                        doc_title=doc.get("title", "Unknown"),
                        clause_type=clause_type,
                        extracted_value="",
                        status=ExtractionStatus.UNRESOLVED,
                        evidence=[],
                        explanation="Two-pass verification failed: extracted text doesn't match clause type",
                        snippet="",
                        page_number=1,
                        confidence=0.0,
                        verified=False,
                        flagged=False,
                    ), None
            except Exception as e:
                logger.warning(f"Verification failed, marking as needs_review: {e}")
                # Don't fail completely, just lower confidence
        
        # STEP 3: Calculate confidence based on keyword analysis
        has_snippet = bool(snippet)
        confidence = calculate_confidence(clause_type, combined_text, has_snippet)
        
        # STEP 4: Find char range for evidence linking
        char_start = result.get("char_start", 0)
        if snippet and char_start == 0:
            # Try to find snippet in content
            snippet_pos = content.find(snippet[:50])  # Match first 50 chars
            if snippet_pos >= 0:
                char_start = snippet_pos
        char_end = char_start + len(snippet) if snippet else char_start
        
        # STEP 5: Create Evidence object
        evidence_list = []
        if snippet:
            evidence_list.append(Evidence(
                file=doc.get("title", "Unknown"),
                page=result.get("page_number", 1),
                snippet=snippet[:500],
                char_start=char_start,
                char_end=char_end,
            ))
        
        # STEP 6: Determine status based on evidence-gated logic
        # HARD RULE: RESOLVED only if evidence exists AND confidence >= 0.8
        if evidence_list and confidence >= 0.8:
            status = ExtractionStatus.RESOLVED
        elif evidence_list:
            status = ExtractionStatus.NEEDS_REVIEW
        else:
            status = ExtractionStatus.UNRESOLVED
        
        # Create extraction with calculated confidence and status
        extraction = ClauseExtraction(
            doc_id=doc["doc_id"],
            doc_title=doc.get("title", "Unknown"),
            clause_type=clause_type,
            extracted_value=extracted_value,
            status=status,
            evidence=evidence_list,
            explanation=result.get("explanation", f"Extracted with {confidence:.0%} confidence"),
            snippet=snippet[:500],  # Keep for backwards compat
            page_number=result.get("page_number", 1), 
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
                "status": e.status.value,
                "evidence": [ev.to_dict() for ev in e.evidence],
                "explanation": e.explanation,
                "snippet": e.snippet,
                "page_number": e.page_number,
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
