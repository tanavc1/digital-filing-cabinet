import logging
import json
from typing import Dict, Optional

from llm_providers import get_llm_provider


logger = logging.getLogger(__name__)

# M&A Document Categories
DOC_TYPES = [
    "NDA / Confidentiality Agreement",
    "Commercial Lease",
    "Employment Agreement",
    "Software License / SaaS",
    "Vendor Contract",
    "Board Resolution / Minutes",
    "Financial Statement",
    "Tax Return",
    "Organizational Chart",
    "Certificate of Incorporation",
    "Stock Purchase Agreement",
    "Merger Agreement",
    "Other/Unclassified"
]

class DocumentClassifier:
    """
    Classifies documents into M&A categories using the configured LLM provider.
    """
    def __init__(self, provider_type: str = "ollama"):
        self.provider = get_llm_provider(provider_type)

    async def classify(self, text: str, filename: str) -> Dict[str, str]:
        """
        Returns {
            "doc_type": "...",
            "confidence": "...",
            "risk_level": "..." (preliminary assessment)
        }
        """
        # Truncate text to avoid token limits, just header is usually enough for classification
        sample_text = text[:4000] 
        
        prompt = f"""You are an expert M&A lawyer. Classify the following document into one of these categories:
{json.dumps(DOC_TYPES, indent=2)}

Also assess the preliminary risk level based on the document type (e.g. Leases and IP licenses are usually Medium/High risk).

Input Document:
Filename: {filename}
Text Sample:
{sample_text}

Respond in strict JSON format:
{{
    "doc_type": "Selected Category",
    "confidence": "High/Medium/Low",
    "risk_level": "High/Medium/Low/Clean",
    "reasoning": "Brief explanation"
}}
"""
        
        try:
            result = await self.provider.complete_json(prompt)
            
            # Normalize fields
            doc_type = result.get("doc_type", "Other/Unclassified")
            if doc_type not in DOC_TYPES:
                 # Check fuzzy match or default
                 doc_type = "Other/Unclassified"
            
            return {
                "doc_type": doc_type,
                "confidence": result.get("confidence", "Low"),
                "risk_level": result.get("risk_level", "Unknown"),
                "reasoning": result.get("reasoning", "")
            }
            
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return {
                "doc_type": "Unclassified",
                "confidence": "None", 
                "risk_level": "Unknown",
                "reasoning": f"Error: {e}"
            }
