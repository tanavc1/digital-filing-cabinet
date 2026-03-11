"""
Digital Filing Cabinet - Core Package
=====================================

Modular RAG engine components:
- config: Application configuration
- utils: Shared utilities (text normalization, scoring, etc.)
- chunking: Document text chunking with overlap
- store: LanceDB vector storage
- bm25: BM25 keyword index
- models: Local embedding and reranking models
- llm: LLM provider abstraction (summarize, extract, synthesize)
- engine: RAGEngine orchestrator
"""

from core.config import Config, DEFAULT_WORKSPACE_ID
from core.engine import RAGEngine, EvidenceContract

__all__ = ["Config", "RAGEngine", "EvidenceContract", "DEFAULT_WORKSPACE_ID"]
