"""
Local embedding and reranking models with lazy loading.
Optimized for Apple Silicon (MPS).
"""
import logging
from typing import List, Dict

import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder


logger = logging.getLogger("rag_lancedb")


def _get_optimal_device() -> str:
    """Determine the best device for model inference."""
    try:
        import torch
        if torch.backends.mps.is_available():
            logger.info("Using MPS (Apple Silicon) for inference")
            return "mps"
        elif torch.cuda.is_available():
            logger.info("Using CUDA for inference")
            return "cuda"
    except ImportError:
        pass
    logger.info("Using CPU for inference")
    return "cpu"


class LocalModels:
    """
    Lazy-loading wrapper for embedding and reranking models.
    Optimized for Apple Silicon (MPS) with explicit device placement.
    """

    def __init__(self, embed_name: str, rerank_name: str, embed_batch_size: int = 64):
        self._embed_name = embed_name
        self._rerank_name = rerank_name
        self._embed_batch_size = embed_batch_size
        self._embedder = None
        self._reranker = None
        self._device = None
        self._load_attempted_reranker = False

    @property
    def device(self) -> str:
        if self._device is None:
            self._device = _get_optimal_device()
        return self._device

    @property
    def embedder(self):
        """Lazy load the embedding model on first use."""
        if self._embedder is None:
            logger.info(f"Loading embed model: {self._embed_name}")
            self._embedder = SentenceTransformer(
                self._embed_name,
                device=self.device,
                model_kwargs={"low_cpu_mem_usage": True}
            )
            logger.info(f"Embed model loaded on device: {self.device}")
        return self._embedder

    @property
    def reranker(self):
        """Lazy load the reranking model on first use."""
        if self._reranker is None and not self._load_attempted_reranker:
            self._load_attempted_reranker = True
            try:
                logger.info(f"Loading rerank model: {self._rerank_name}")
                self._reranker = CrossEncoder(
                    self._rerank_name,
                    device=self.device,
                    model_kwargs={"low_cpu_mem_usage": True}
                )
                logger.info(f"Rerank model loaded on device: {self.device}")
            except Exception as e:
                logger.error(f"Failed to load Rerank model: {e}")
                logger.warning("Proceeding without Reranker (Semantic Search only).")
        return self._reranker

    def embed(self, texts: List[str], batch_size: int = 0) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        bs = batch_size if batch_size > 0 else self._embed_batch_size
        vecs = self.embedder.encode(
            texts,
            batch_size=bs,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return [v.astype(np.float32).tolist() for v in vecs]

    def embed_one(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        return self.embed([text])[0]

    def rerank(self, query: str, candidates: List[Dict]) -> List[Dict]:
        """Rerank candidates based on query relevance."""
        if not candidates:
            return []

        if self.reranker is None:
            return candidates

        pairs = [(query, c["text"]) for c in candidates]
        scores = self.reranker.predict(pairs)
        out = []
        for c, s in zip(candidates, scores):
            cc = dict(c)
            cc["_rerank_score"] = float(s)
            out.append(cc)
        out.sort(key=lambda x: x["_rerank_score"], reverse=True)
        return out

    def warmup(self):
        """Pre-load models to avoid cold start latency."""
        logger.info("Warming up LocalModels...")
        _ = self.embedder
        _ = self.reranker
        logger.info("LocalModels warmup complete")
