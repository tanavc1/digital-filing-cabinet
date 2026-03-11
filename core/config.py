"""
Configuration for the Digital Filing Cabinet RAG engine.
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv
import logging

logger = logging.getLogger("rag_lancedb")


# ----------------------------
# Workspace defaults
# ----------------------------
DEFAULT_WORKSPACE_ID = os.getenv("DEFAULT_WORKSPACE_ID", "default")


@dataclass
class Config:
    db_path: str
    openai_api_key: str
    openai_model_id: str

    embed_model_name: str
    rerank_model_name: str

    chunk_size_chars: int
    chunk_overlap_ratio: float

    topk_bm25: int
    topk_vector: int
    topk_fused: int
    topk_rerank: int
    rrf_k: int
    rrf_alpha: float

    # Calibrated abstain logic
    min_rerank_norm: float
    min_term_overlap: float
    min_retrieval_agreement: int

    # Rerank threshold
    min_rerank_score: float

    # Safe, additive knobs
    source_score_drop: float
    answer_only_question: bool
    enable_dedupe: bool
    rescue_multifact: bool
    rescue_deferred: bool

    # Performance tuning
    embed_batch_size: int = 64
    llm_timeout: float = 120.0
    ollama_num_ctx: int = 4096

    def __post_init__(self):
        """Validate configuration values."""
        if self.chunk_size_chars <= 0:
            raise ValueError(f"chunk_size_chars must be > 0, got {self.chunk_size_chars}")
        if not (0.0 < self.chunk_overlap_ratio < 1.0):
            raise ValueError(f"chunk_overlap_ratio must be in (0, 1), got {self.chunk_overlap_ratio}")
        if self.topk_bm25 <= 0 or self.topk_vector <= 0:
            raise ValueError("topk values must be positive")
        if self.llm_timeout <= 0:
            raise ValueError(f"llm_timeout must be > 0, got {self.llm_timeout}")
        if self.embed_batch_size <= 0:
            raise ValueError(f"embed_batch_size must be > 0, got {self.embed_batch_size}")

    @staticmethod
    def from_env(db_path: str) -> "Config":
        load_dotenv()

        def getenv_required(k: str) -> str:
            v = os.getenv(k)
            if not v:
                raise RuntimeError(f"Missing required env var: {k}")
            return v

        def getenv_bool(k: str, default: str = "1") -> bool:
            v = os.getenv(k, default).strip().lower()
            return v in ("1", "true", "yes", "y", "on")

        return Config(
            db_path=db_path,
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model_id=os.getenv("OPENAI_MODEL_ID", "gpt-5-nano-2025-08-07"),

            embed_model_name=os.getenv("EMBED_MODEL_NAME", "BAAI/bge-small-en-v1.5"),
            rerank_model_name=os.getenv("RERANK_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2"),

            chunk_size_chars=int(os.getenv("CHUNK_SIZE_CHARS", "3000")),
            chunk_overlap_ratio=float(os.getenv("CHUNK_OVERLAP_RATIO", "0.20")),

            topk_bm25=int(os.getenv("TOPK_BM25", "20")),
            topk_vector=int(os.getenv("TOPK_VECTOR", "20")),
            topk_fused=int(os.getenv("TOPK_FUSED", "20")),
            topk_rerank=int(os.getenv("TOPK_RERANK", "10")),
            rrf_k=int(os.getenv("RRF_K", "60")),
            rrf_alpha=float(os.getenv("RRF_ALPHA", "0.5")),

            min_rerank_norm=float(os.getenv("MIN_RERANK_NORM", "0.55")),
            min_term_overlap=float(os.getenv("MIN_TERM_OVERLAP", "0.08")),
            min_retrieval_agreement=int(os.getenv("MIN_RETRIEVAL_AGREEMENT", "1")),

            min_rerank_score=float(os.getenv("MIN_RERANK_SCORE", "0.10")),

            source_score_drop=float(os.getenv("SOURCE_SCORE_DROP", "4.0")),
            answer_only_question=getenv_bool("ANSWER_ONLY_QUESTION", "1"),
            enable_dedupe=getenv_bool("ENABLE_DEDUPE", "1"),
            rescue_multifact=getenv_bool("RESCUE_MULTIFACT", "1"),
            rescue_deferred=getenv_bool("RESCUE_DEFERRED", "1"),

            # Performance tuning
            embed_batch_size=int(os.getenv("EMBED_BATCH_SIZE", "64")),
            llm_timeout=float(os.getenv("LLM_TIMEOUT", "120.0")),
            ollama_num_ctx=int(os.getenv("OLLAMA_NUM_CTX", "4096")),
        )
