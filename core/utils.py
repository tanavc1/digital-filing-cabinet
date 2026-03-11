"""
Shared utility functions for the Digital Filing Cabinet.
"""
import os
import re
import time
import hashlib
from typing import List, Dict, Optional
from collections import defaultdict


# ----------------------------
# Compiled Patterns
# ----------------------------
_WORD_RE = re.compile(r"[A-Za-z0-9_]+")
_MONEY_RE = re.compile(r"\$\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?|\$\s?\d+(?:\.\d+)?", re.IGNORECASE)
_PERCENT_RE = re.compile(r"\b\d+(?:\.\d+)?\s?%\b")
_RISK_HINTS = ("risk", "concern", "downside", "lock-in", "lock in", "lockin", "disruption", "penalty", "sla", "capacity")


# ----------------------------
# Core Helpers
# ----------------------------
def now_ts() -> int:
    return int(time.time())


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join([ln.rstrip() for ln in text.split("\n")])
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def tokenize_for_bm25(text: str) -> List[str]:
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


def normalize_scores(scores: List[float]) -> List[float]:
    if not scores:
        return []
    mn, mx = min(scores), max(scores)
    if mx - mn < 1e-6:
        return [0.5 for _ in scores]
    return [(s - mn) / (mx - mn) for s in scores]


def safe_mkdir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def clip_excerpt(text: str, n: int = 240) -> str:
    t = text.replace("\n", " ").strip()
    return t[:n] + ("..." if len(t) > n else "")


# ----------------------------
# Workspace Helpers
# ----------------------------
def normalize_workspace_id(ws: Optional[str]) -> str:
    from core.config import DEFAULT_WORKSPACE_ID
    return (ws or DEFAULT_WORKSPACE_ID).strip()


def _row_workspace_id(r: Dict) -> str:
    from core.config import DEFAULT_WORKSPACE_ID
    return r.get("workspace_id", DEFAULT_WORKSPACE_ID)


def _safe_ws_filename(ws: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", ws)


# ----------------------------
# Query Classification
# ----------------------------
def term_overlap_ratio(query: str, text: str) -> float:
    q = set(tokenize_for_bm25(query))
    if not q:
        return 0.0
    t = set(tokenize_for_bm25(text))
    return len(q.intersection(t)) / max(1, len(q))


def infer_chunk_type(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("decision summary", "decision", "approved", "rejected", "not approved")):
        return "decision"
    if any(k in t for k in ("follow-up", "follow up", "next steps", "action", "actions")):
        return "follow_up"
    if any(k in t for k in ("board commentary", "board", "commentary")):
        return "board"
    if any(k in t for k in ("background", "context", "executive context")):
        return "background"
    return "discussion"


def is_deferred_query(q: str) -> bool:
    t = q.lower()
    return any(phrase in t for phrase in (
        "defer", "deferred",
        "revisit", "revisited",
        "re-evaluate", "reevaluate", "reassess", "reassessment",
        "not approved", "not approved at this time",
        "rather than rejected", "rather than fully rejected",
        "when will they be revisited", "be revisited"
    ))


def is_multifact_tradeoff_query(q: str) -> bool:
    t = q.lower()
    return (
        ("largest" in t or "most" in t or "biggest" in t)
        and ("risk" in t or "risks" in t or "accepted" in t or "tradeoff" in t or "in exchange" in t)
        and ("savings" in t or "cost" in t or "save" in t)
    )


def chunk_has_money_or_percent(text: str) -> bool:
    return bool(_MONEY_RE.search(text) or _PERCENT_RE.search(text))


def chunk_has_risk_terms(text: str) -> bool:
    t = text.lower()
    return any(h in t for h in _RISK_HINTS)


# Default phrases for defer/revisit detection. Override via DEFER_PHRASES env or custom config.
_DEFAULT_DEFER_PHRASES = (
    "not approved at this time",
    "not approved",
    "revisit",
    "re-evaluate", "reevaluate",
    "reassess", "reassessment",
    "requested", "updated plan",
)


def chunk_mentions_defer_revisit(text: str, extra_phrases: tuple = ()) -> bool:
    t = text.lower()
    phrases = _DEFAULT_DEFER_PHRASES + extra_phrases
    return any(phrase in t for phrase in phrases)


# ----------------------------
# RRF Fusion
# ----------------------------
def rrf_fusion(
    bm25_hits: List[Dict],
    vec_hits: List[Dict],
    alpha: float = 0.5,
    k: int = 60
) -> List[Dict]:
    """Reciprocal Rank Fusion (convenience wrapper around rrf_fuse)."""
    return rrf_fuse(bm25_hits, vec_hits, key="chunk_id", k=k, limit=len(bm25_hits) + len(vec_hits))


def rrf_fuse(
    ranked_a: List[Dict],
    ranked_b: List[Dict],
    key: str = "chunk_id",
    k: int = 60,
    limit: int = 60
) -> List[Dict]:
    """Alternative RRF fusion with configurable key."""
    scores = defaultdict(float)
    meta = {}

    def add_list(lst: List[Dict]):
        for rank, hit in enumerate(lst):
            cid = hit[key]
            scores[cid] += 1.0 / (k + rank + 1)
            if cid not in meta:
                meta[cid] = hit

    add_list(ranked_a)
    add_list(ranked_b)

    out = []
    for cid, s in sorted(scores.items(), key=lambda x: -x[1]):
        row = dict(meta[cid])
        row["_rrf_score"] = s
        out.append(row)
    return out[:limit]
