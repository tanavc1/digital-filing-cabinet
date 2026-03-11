"""
BM25 keyword index with persistence.
"""
import logging
from typing import List, Dict

import numpy as np
from joblib import dump, load as jl_load
from rank_bm25 import BM25Okapi

from core.config import DEFAULT_WORKSPACE_ID
from core.utils import tokenize_for_bm25


logger = logging.getLogger("rag_lancedb")


class BM25Index:
    """
    BM25 keyword search index with persistence.
    Builds from chunk data and supports save/load via joblib.
    """
    def __init__(self, bm25: BM25Okapi, corpus_tokens: List[List[str]], meta: List[Dict]):
        self.bm25 = bm25
        self.corpus_tokens = corpus_tokens
        self.meta = meta

    @staticmethod
    def build(chunks: List[Dict]) -> "BM25Index":
        meta = []
        corpus_tokens = []
        for r in chunks:
            meta.append({
                "chunk_id": r["chunk_id"],
                "doc_id": r["doc_id"],
                "workspace_id": r.get("workspace_id") or DEFAULT_WORKSPACE_ID,
                "chunk_index": r["chunk_index"],
                "start_char": r["start_char"],
                "end_char": r["end_char"],
                "text": r["text"],
                "chunk_type": r.get("chunk_type", "discussion"),
            })
            corpus_tokens.append(tokenize_for_bm25(r["text"]))
        bm25 = BM25Okapi(corpus_tokens)
        return BM25Index(bm25=bm25, corpus_tokens=corpus_tokens, meta=meta)

    def save(self, path: str) -> None:
        dump({"bm25": self.bm25, "corpus_tokens": self.corpus_tokens, "meta": self.meta}, path)

    @staticmethod
    def load(path: str) -> "BM25Index":
        obj = jl_load(path)
        return BM25Index(bm25=obj["bm25"], corpus_tokens=obj["corpus_tokens"], meta=obj["meta"])

    def search(self, query: str, topk: int) -> List[Dict]:
        qtok = tokenize_for_bm25(query)
        scores = self.bm25.get_scores(qtok)
        if len(scores) == 0:
            return []
        top_idx = np.argsort(scores)[::-1][:topk]
        results = []
        for i in top_idx:
            if scores[i] <= 0:
                continue
            r = dict(self.meta[int(i)])
            r["_bm25_score"] = float(scores[int(i)])
            results.append(r)
        return results
