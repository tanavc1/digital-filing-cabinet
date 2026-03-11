"""
RAG Engine — Main orchestrator for the Digital Filing Cabinet pipeline.

Responsibilities:
1. Ingestion: Files/URLs → Docling → Chunking → Embedding → LanceDB
2. Retrieval: Hybrid Search (BM25 + Vector) → RRF Fusion → Reranking
3. Evidence: Extraction → Fuzzy Verification → Deduplication
4. Synthesis: Answer generation with streaming support
"""
import os
import re
import json
import uuid
import hashlib
import logging
import asyncio
from typing import List, Dict, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field

from rapidfuzz import fuzz
from tqdm import tqdm

from core.config import Config, DEFAULT_WORKSPACE_ID
from core.utils import (
    now_ts, sha256_hex, normalize_text, normalize_workspace_id,
    _row_workspace_id, _safe_ws_filename, safe_mkdir,
    clip_excerpt, term_overlap_ratio,
    is_deferred_query, is_multifact_tradeoff_query,
    chunk_has_money_or_percent, chunk_has_risk_terms,
    chunk_mentions_defer_revisit, normalize_scores,
    rrf_fusion, rrf_fuse,
)
from core.chunking import chunk_text_with_overlap
from core.store import LanceStore
from core.bm25 import BM25Index
from core.models import LocalModels
from core.llm import NanoLLM

from classifiers import DocumentClassifier
from docling_loader import DoclingExtractor


logger = logging.getLogger("rag_lancedb")


# ----------------------------
# Evidence Contract
# ----------------------------
@dataclass
class EvidenceContract:
    """Mandatory Evidence Schema (Phase 8).
    The System of Record for all answers.
    """
    evidence_id: str
    workspace_id: str
    doc_id: str
    start_char: int
    end_char: int
    quote: str
    content_hash: str
    confidence: float
    verified: bool = True
    page_or_slide: Optional[int] = None

    def dict(self):
        return {k: v for k, v in self.__dict__.items()}


# ----------------------------
# RAG Engine
# ----------------------------
class RAGEngine:
    """
    Main Orchestrator for the RAG Pipeline.

    Responsibilities:
    1. Ingestion: Accepts files/URLs -> Docling -> Chunking -> LanceDB.
    2. Retrieval: list_docs, delete_doc, rebuild_bm25.
    3. Querying: Hybrid Search (BM25 + Vector) -> RRF Fusion -> Evidence Extraction -> Synthesis.
    4. Streaming: Query stream generator for SSE.
    """
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.store = LanceStore(cfg.db_path)
        self.models = LocalModels(cfg.embed_model_name, cfg.rerank_model_name, embed_batch_size=cfg.embed_batch_size)
        self.llm = NanoLLM(cfg)
        self.nanollm = NanoLLM(cfg)
        self.doc_loader = DoclingExtractor()
        self.classifier = DocumentClassifier()

        self.bm25_dir = os.path.join(cfg.db_path, "bm25")
        safe_mkdir(self.bm25_dir)

        # In-memory BM25 cache: workspace_id -> BM25Index
        self._bm25_cache: Dict[str, BM25Index] = {}

    def _bm25_path(self, workspace_id: str) -> str:
        safe_ws = _safe_ws_filename(workspace_id)
        return os.path.join(self.bm25_dir, f"bm25_{safe_ws}.joblib")

    # ----------------------------
    # Stats & Metadata
    # ----------------------------
    def get_risk_stats(self, workspace_id: str) -> Dict[str, Any]:
        """Aggregates risk and document type statistics for the dashboard."""
        docs = self.store.list_documents(workspace_id)

        total_docs = len(docs)
        risk_counts = {"High": 0, "Medium": 0, "Low": 0, "Clean": 0, "Unknown": 0}
        type_counts = {}
        folder_risks = {}

        for d in docs:
            r = d.get("risk_level", "Unknown")
            if r not in risk_counts:
                r = "Unknown"
            risk_counts[r] += 1

            t = d.get("doc_type", "Unclassified")
            type_counts[t] = type_counts.get(t, 0) + 1

            f = d.get("folder_path", "/").strip()
            if not f:
                f = "/"
            if f not in folder_risks:
                folder_risks[f] = {"High": 0, "total": 0}
            folder_risks[f]["total"] += 1
            if r == "High":
                folder_risks[f]["High"] += 1

        return {
            "total_docs": total_docs,
            "risk_counts": risk_counts,
            "type_counts": type_counts,
            "folder_risks": folder_risks
        }

    # ----------------------------
    # Ingestion
    # ----------------------------
    async def ingest_text_file(
        self,
        path: str,
        title: str = "",
        source: str = "local",
        workspace_id: str = DEFAULT_WORKSPACE_ID,
        uri: str = "",
        folder_path: str = "/",
        progress_callback: Optional[Callable] = None,
    ) -> str:
        """
        Ingests a document (text, PDF, DOCX, images) using Docling or raw read.
        Chunks it, extracts metadata, runs classification, generates summary/embedding, and upserts.
        """
        if not uri:
            uri = f"file://{path}"

        workspace_id = normalize_workspace_id(workspace_id)

        if not os.path.exists(path):
            raise FileNotFoundError(path)

        # Use DoclingExtractor for robust text extraction
        logger.info(f"Loading document with Docling: {path}")
        try:
            doc_result = self.doc_loader.extract(path, title=title)
            full_text = doc_result.text.strip()
            final_title = title or doc_result.title or os.path.basename(path)
        except Exception as e:
            logger.warning(f"Docling extraction failed, falling back to raw read: {e}")
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                full_text = f.read().strip()
            final_title = title or os.path.basename(path)

        if not full_text:
            logger.warning(f"File {path} is empty or unreadable.")
            return ""

        # Run M&A Classification
        logger.info(f"Running M&A classification for: {final_title}")
        cls_result = await self.classifier.classify(full_text, final_title)

        doc_type = cls_result["doc_type"]
        risk_level = cls_result["risk_level"]
        logger.info(f"Classified as: {doc_type} (Risk: {risk_level})")

        # Determine content hash
        content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()

        # Safe dedupe: avoids duplicates + avoids extra LLM calls
        if self.cfg.enable_dedupe:
            existing = self.store.fetch_document_by_content_hash(workspace_id, content_hash)
            if existing:
                logger.info(f"Duplicate content detected; skipping ingest. (doc_id={existing['doc_id']})")
                return existing["doc_id"]

        doc_id = str(uuid.uuid4())
        logger.info(f"Ingesting doc: {final_title} (workspace_id={workspace_id}, doc_id={doc_id})")

        if progress_callback:
            await progress_callback({"stage": "summarizing", "percent": 10})

        summary = await self.llm.summarize_doc(text=full_text, title=final_title)

        chunks = chunk_text_with_overlap(
            text=full_text,
            chunk_size_chars=self.cfg.chunk_size_chars,
            overlap_ratio=self.cfg.chunk_overlap_ratio,
        )
        logger.info(f"Chunked into {len(chunks)} chunks")

        if progress_callback:
            await progress_callback({"stage": "chunking", "percent": 20, "chunks": len(chunks)})

        chunk_texts = [c["text"] for c in chunks]
        embeddings: List[List[float]] = []
        total_chunks = len(chunk_texts)
        for i in tqdm(range(0, total_chunks, 64), desc="Embedding chunks"):
            batch = chunk_texts[i:i + 64]
            embeddings.extend(
                await asyncio.to_thread(self.models.embed, batch)
            )
            if progress_callback:
                progress = 20 + int((i / total_chunks) * 60)
                await progress_callback({"stage": "embedding", "percent": progress, "current": i, "total": total_chunks})

        chunk_rows = []
        for c, emb in zip(chunks, embeddings):
            chunk_id = f"chunk_{doc_id}_{c['chunk_index']}"
            chunk_rows.append({
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "workspace_id": workspace_id,
                "source": source,
                "uri": uri,
                "folder_path": folder_path,
                "title": final_title,
                "chunk_index": int(c["chunk_index"]),
                "start_char": int(c["start_char"]),
                "end_char": int(c["end_char"]),
                "text": c["text"],
                "chunk_type": c.get("chunk_type", "discussion"),
                "embedding": emb,
                "created_at": now_ts(),
                "content_hash": content_hash,
            })

        self.store.upsert_chunks(chunk_rows)

        doc_row = {
            "doc_id": doc_id,
            "workspace_id": workspace_id,
            "source": source,
            "uri": uri,
            "folder_path": folder_path,
            "title": final_title,
            "created_at": now_ts(),
            "modified_at": now_ts(),
            "content_hash": content_hash,
            "summary_text": summary,
            "summary_model": "ollama",
            "summary_version": "v3",
            "doc_type": doc_type,
            "risk_level": risk_level,
        }
        self.store.upsert_document(doc_row)

        # Rebuild BM25 for this workspace
        self.rebuild_bm25(workspace_id=workspace_id)

        logger.info("Ingest complete.")
        return doc_id

    # ----------------------------
    # BM25 Management
    # ----------------------------
    def rebuild_bm25(self, workspace_id: Optional[str] = None) -> None:
        workspace_id = normalize_workspace_id(workspace_id)
        logger.info(f"Rebuilding BM25 index (workspace_id={workspace_id})...")
        chunks = self.store.load_all_chunks_minimal(workspace_id=workspace_id)
        if not chunks:
            raise RuntimeError(f"No chunks found for workspace '{workspace_id}'.")
        bm25 = BM25Index.build(chunks)
        path = self._bm25_path(workspace_id)
        bm25.save(path)
        self._bm25_cache[workspace_id] = bm25
        logger.info(f"BM25 saved to {path} and cached in memory")

    def _load_bm25(self, workspace_id: Optional[str] = None) -> BM25Index:
        workspace_id = normalize_workspace_id(workspace_id)
        # Check memory cache first
        if workspace_id in self._bm25_cache:
            return self._bm25_cache[workspace_id]
        # Load from disk
        path = self._bm25_path(workspace_id)
        if not os.path.exists(path):
            self.rebuild_bm25(workspace_id=workspace_id)
            return self._bm25_cache[workspace_id]
        bm25 = BM25Index.load(path)
        self._bm25_cache[workspace_id] = bm25
        return bm25

    # ----------------------------
    # Document Access
    # ----------------------------
    async def get_doc_text(self, doc_id: str, workspace_id: Optional[str] = None) -> Optional[str]:
        workspace_id = normalize_workspace_id(workspace_id)
        doc = self.store.fetch_document(workspace_id, doc_id)
        if doc and doc.get("full_text"):
            return doc.get("full_text")

        chunks = self.store.fetch_chunks_for_doc(workspace_id, doc_id)
        if not chunks:
            return None

        full_text = "\n\n".join([c.get("text", "") for c in chunks])
        return full_text

    def list_docs(self, workspace_id: Optional[str] = None) -> List[Dict]:
        workspace_id = normalize_workspace_id(workspace_id)
        return self.store.list_documents(workspace_id)

    def delete_doc(self, doc_id: str, workspace_id: Optional[str] = None) -> bool:
        workspace_id = normalize_workspace_id(workspace_id)
        ok = self.store.delete_document(workspace_id, doc_id)
        try:
            chunks = self.store.load_all_chunks_minimal(workspace_id=workspace_id)
            if chunks:
                self.rebuild_bm25(workspace_id=workspace_id)
        except Exception as e:
            logger.info(f"(warn) BM25 rebuild after delete skipped/failed: {e}")
        return ok

    # ----------------------------
    # Evidence Verification
    # ----------------------------
    def _verify_evidence_match(self, evidence_item: Dict, windows: List[Dict]) -> Optional[EvidenceContract]:
        """
        Verify that evidence_item['quote'] exists using robust fuzzy matching.
        Handles smart quotes, whitespace differences, and cross-chunk spans.
        """
        quote = evidence_item.get("quote", "").strip()
        doc_id = evidence_item.get("doc_id")

        if not quote or not doc_id:
            return None

        target_window = next((w for w in windows if w["doc_id"] == doc_id), None)
        if not target_window:
            return None

        window_text = target_window["window_text"]
        chunks = target_window.get("chunks", [])
        workspace_id = chunks[0].get("workspace_id", "default") if chunks else "default"

        # Handle Ellipsis (Split Verification)
        if "..." in quote:
            parts = [p.strip() for p in quote.split("...") if p.strip()]
            all_parts_found = True
            min_start = float('inf')
            max_end = -1

            for p in parts:
                p_align = fuzz.partial_ratio_alignment(p, window_text)
                if not p_align or p_align.score < 85.0:
                    all_parts_found = False
                    break
                min_start = min(min_start, p_align.dest_start)
                max_end = max(max_end, p_align.dest_end)

            if all_parts_found:
                verified_text = window_text[min_start:max_end]
                m_start = min_start
                m_end = max_end
                alignment = p_align
            else:
                tsr_score = fuzz.token_set_ratio(quote, window_text)
                if tsr_score >= 90.0:
                    quote_lower = quote.lower()
                    window_lower = window_text.lower()
                    match_pos = window_lower.find(quote_lower[:50])
                    if match_pos == -1:
                        match_pos = 0

                    return EvidenceContract(
                        evidence_id=str(uuid.uuid4()),
                        doc_id=doc_id,
                        workspace_id=workspace_id,
                        quote=quote,
                        start_char=match_pos,
                        end_char=match_pos + len(quote),
                        content_hash=hashlib.sha256(quote.encode()).hexdigest(),
                        confidence=0.9,
                        verified=True,
                        page_or_slide=None
                    )
                return None
        else:
            # Standard Fuzzy Search
            alignment = fuzz.partial_ratio_alignment(quote, window_text)
            if not alignment or alignment.score < 85.0:
                tsr_score = fuzz.token_set_ratio(quote, window_text)
                if tsr_score >= 90.0:
                    quote_lower = quote.lower()
                    window_lower = window_text.lower()
                    match_pos = window_lower.find(quote_lower[:50])
                    if match_pos == -1:
                        match_pos = 0

                    return EvidenceContract(
                        evidence_id=str(uuid.uuid4()),
                        doc_id=doc_id,
                        workspace_id=workspace_id,
                        quote=quote,
                        start_char=match_pos,
                        end_char=match_pos + len(quote),
                        content_hash=hashlib.sha256(quote.encode()).hexdigest(),
                        confidence=0.9,
                        verified=True,
                        page_or_slide=None
                    )
                return None

        # Confirmed Match — Map to global offsets
        m_start = alignment.dest_start
        m_end = alignment.dest_end
        verified_text = window_text[m_start:m_end]

        current_pos = 0
        global_start = -1
        global_end = -1
        workspace_id = chunks[0].get("workspace_id", "default") if chunks else "default"

        for chunk in chunks:
            chunk_text = chunk["text"]
            chunk_len = len(chunk_text)
            chunk_window_start = current_pos
            chunk_window_end = current_pos + chunk_len

            if chunk_window_start <= m_start < chunk_window_end + 1:
                offset_in_chunk = max(0, m_start - chunk_window_start)
                if "start_char" in chunk:
                    global_start = chunk["start_char"] + offset_in_chunk
                    global_end = global_start + (m_end - m_start)
                else:
                    global_start = 0
                    global_end = 0
                break

            current_pos += chunk_len + 1

        if global_start != -1:
            verified_hash = hashlib.sha256(verified_text.encode("utf-8")).hexdigest()
            return EvidenceContract(
                evidence_id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                doc_id=doc_id,
                start_char=global_start,
                end_char=global_end,
                quote=verified_text,
                content_hash=verified_hash,
                confidence=alignment.score / 100.0,
                verified=True,
                page_or_slide=None
            )

        return None

    def _merge_adjacent_evidence(self, verified_list: List[EvidenceContract]) -> List[EvidenceContract]:
        """Merge adjacent evidence chunks from the same document."""
        if not verified_list:
            return []

        sorted_list = sorted(verified_list, key=lambda x: (x.doc_id, x.start_char))
        merged = []
        current = sorted_list[0]

        for next_item in sorted_list[1:]:
            is_same_doc = (current.doc_id == next_item.doc_id)
            gap = next_item.start_char - current.end_char
            is_connected = (gap <= 15)

            if is_same_doc and is_connected:
                new_end = max(current.end_char, next_item.end_char)
                sep = " "
                if gap > 2:
                    sep = " [...] "
                current.quote = current.quote + sep + next_item.quote
                current.end_char = new_end
                current.confidence = max(current.confidence, next_item.confidence)
            else:
                merged.append(current)
                current = next_item

        merged.append(current)
        return merged

    # ----------------------------
    # Retrieval Helpers
    # ----------------------------
    def _select_good_sources(self, reranked: List[Dict]) -> List[Dict]:
        if not reranked:
            return []

        first_score = reranked[0].get("_rerank_score")
        if first_score is None or (isinstance(first_score, float) and not (first_score == first_score)):
            logger.info(f"No valid rerank scores found - returning all {len(reranked)} candidates without filtering")
            return reranked

        top_score = reranked[0]["_rerank_score"]
        floor = top_score - self.cfg.source_score_drop
        good = [c for c in reranked if c.get("_rerank_score", float('-inf')) >= floor]
        logger.info(f"Score filtering: top={top_score:.2f}, floor={floor:.2f}, kept {len(good)}/{len(reranked)}")
        return good

    async def _retrieve_candidates(
        self,
        question: str,
        workspace_id: Optional[str] = None,
        doc_ids: Optional[List[str]] = None,
        folder_path: Optional[str] = None
    ) -> List[Dict]:
        """Parallel retrieval + RRF Fusion + Reranking + Score Filtering."""
        workspace_id = normalize_workspace_id(workspace_id)
        bm25 = self._load_bm25(workspace_id=workspace_id)

        def run_bm25():
            try:
                hits = bm25.search(question, topk=self.cfg.topk_bm25)
                if doc_ids:
                    wanted = set(doc_ids)
                    hits = [r for r in hits if r.get("doc_id") in wanted]
                return hits
            except Exception as e:
                logger.error(f"BM25 search failed: {e}")
                return []

        def run_vector():
            try:
                qvec = self.models.embed_one(question)
                return self.store.vector_search(
                    qvec,
                    limit=self.cfg.topk_vector,
                    workspace_id=workspace_id,
                    doc_ids=doc_ids
                )
            except Exception:
                return []

        bm25_hits, vec_hits = await asyncio.gather(
            asyncio.to_thread(run_bm25),
            asyncio.to_thread(run_vector)
        )

        if not bm25_hits:
            bm25_hits = []
        if not vec_hits:
            vec_hits = []

        logger.info(f"BM25 hits: {len(bm25_hits)}, Vector hits: {len(vec_hits)}")

        vec_hits_norm = []
        for r in vec_hits:
            vec_hits_norm.append({
                "chunk_id": r["chunk_id"],
                "doc_id": r["doc_id"],
                "workspace_id": _row_workspace_id(r),
                "chunk_index": r["chunk_index"],
                "start_char": r["start_char"],
                "end_char": r["end_char"],
                "text": r["text"],
                "chunk_type": r.get("chunk_type", "discussion"),
                "_vector_distance": float(r.get("_distance", r.get("_score", 0.0))) if isinstance(r, dict) else 0.0
            })

        fused_ids = rrf_fuse(
            ranked_a=bm25_hits,
            ranked_b=vec_hits_norm,
            key="chunk_id",
            k=self.cfg.rrf_k,
            limit=self.cfg.topk_fused,
        )
        fused_id_set = [cid for cid, _ in fused_ids]

        candidate_map = {}
        for r in bm25_hits:
            candidate_map[r["chunk_id"]] = {
                "chunk_id": r["chunk_id"],
                "doc_id": r["doc_id"],
                "workspace_id": r.get("workspace_id") or workspace_id,
                "chunk_index": r["chunk_index"],
                "start_char": r["start_char"],
                "end_char": r["end_char"],
                "text": r["text"],
                "chunk_type": r.get("chunk_type", "discussion"),
                "_bm25_score": r.get("_bm25_score", 0.0),
            }
        for r in vec_hits_norm:
            if r["chunk_id"] not in candidate_map:
                candidate_map[r["chunk_id"]] = dict(r)

        fused_candidates = [candidate_map[cid] for cid in fused_id_set if cid in candidate_map]

        if folder_path:
            fused_candidates = [
                c for c in fused_candidates
                if c.get("folder_path", "").startswith(folder_path)
            ]
            logger.info(f"After folder filter ({folder_path}): {len(fused_candidates)}")

        logger.info(f"Fused candidates: {len(fused_candidates)}")

        if not fused_candidates:
            logger.warning("No fused candidates - returning empty")
            return []

        reranked = self.models.rerank(question, fused_candidates)
        logger.info(f"Reranked candidates: {len(reranked)}")

        good_candidates = self._select_good_sources(reranked)
        logger.info(f"Good candidates after filtering: {len(good_candidates)}")
        return good_candidates[:5]

    async def _extract_evidence_batched(self, question: str, candidates: List[Dict]) -> Dict:
        """Construct windows and run multi-step extraction."""
        evidence_windows = []
        for c in candidates:
            ws_id = c.get("workspace_id", "default")
            neighbors = self.store.fetch_neighbor_chunks(
                workspace_id=ws_id,
                doc_id=c["doc_id"],
                center_chunk_index=c["chunk_index"],
                window=2
            )
            full_text = "\n".join([n["text"] for n in neighbors])
            window_chunk_ids = [n["chunk_id"] for n in neighbors]
            evidence_windows.append({
                "window_text": full_text,
                "doc_id": c["doc_id"],
                "chunk_ids": window_chunk_ids,
                "center_chunk_id": c["chunk_id"],
                "chunks": neighbors
            })

        num_candidates = len(evidence_windows)
        if num_candidates <= 10:
            return await self.llm.extract_evidence(question, evidence_windows)
        else:
            tasks = [self.llm.extract_evidence_single(question, w) for w in evidence_windows]
            results = await asyncio.gather(*tasks)
            combined_evidence = []
            combined_explanation = []
            for r in results:
                combined_evidence.extend(r.get("evidence", []))
                if r.get("explanation"):
                    combined_explanation.append(r["explanation"])
            return {
                "evidence": combined_evidence,
                "explanation": " | ".join(combined_explanation)
            }

    # ----------------------------
    # Query (Non-Streaming)
    # ----------------------------
    async def query(
        self,
        question: str,
        workspace_id: Optional[str] = None,
        doc_id: Optional[str] = None,
        doc_ids: Optional[List[str]] = None,
    ) -> Dict:
        workspace_id = normalize_workspace_id(workspace_id)

        scope_doc_ids: Optional[List[str]] = None
        if doc_id:
            scope_doc_ids = [doc_id]
        elif doc_ids:
            scope_doc_ids = list({d for d in doc_ids if d})
            if not scope_doc_ids:
                scope_doc_ids = None

        reranked_good = await self._retrieve_candidates(
            question=question,
            workspace_id=workspace_id,
            doc_ids=scope_doc_ids
        )

        if not reranked_good:
            return {
                "answer": "Not found in the document.",
                "explanation": "No documents available or no relevant matches found.",
                "sources": [],
                "abstained": True,
            }

        top_n = reranked_good[:5]

        # 1. Expand to Evidence Windows (larger context)
        evidence_windows = []
        seen_doc_ids = set()

        for c in top_n:
            if c["doc_id"] in seen_doc_ids:
                continue
            seen_doc_ids.add(c["doc_id"])

            neighbors = self.store.fetch_neighbor_chunks(
                workspace_id=c.get("workspace_id") or workspace_id,
                doc_id=c["doc_id"],
                center_chunk_index=c["chunk_index"],
                window=4
            )
            full_text = "\n".join([n["text"] for n in neighbors])
            window_chunk_ids = [n["chunk_id"] for n in neighbors]
            evidence_windows.append({
                "window_text": full_text,
                "doc_id": c["doc_id"],
                "chunk_ids": window_chunk_ids,
                "center_chunk_id": c["chunk_id"],
                "chunks": neighbors
            })

        # 2. Extract Evidence (with retry)
        MAX_EXTRACTION_ATTEMPTS = 3
        extraction_result = {"evidence": [], "explanation": ""}

        for attempt in range(MAX_EXTRACTION_ATTEMPTS):
            if len(evidence_windows) <= 10:
                extraction_result = await self.llm.extract_evidence(question, evidence_windows)
            else:
                tasks = [self.llm.extract_evidence_single(question, w) for w in evidence_windows]
                results = await asyncio.gather(*tasks)
                combined_ev = []
                combined_expl = []
                for r in results:
                    combined_ev.extend(r.get("evidence", []))
                    if r.get("explanation"):
                        combined_expl.append(r["explanation"])
                extraction_result = {"evidence": combined_ev, "explanation": " | ".join(combined_expl)}

            if extraction_result.get("evidence"):
                break
            if attempt < MAX_EXTRACTION_ATTEMPTS - 1:
                logger.info(f"Extraction attempt {attempt + 1} returned empty, retrying...")

        # 3. Verify Evidence
        raw_evidence = extraction_result.get("evidence", [])
        verified_evidence: List[EvidenceContract] = []
        seen_quotes = set()

        for item in raw_evidence:
            v_item = self._verify_evidence_match(item, evidence_windows)
            if v_item:
                quote_key = " ".join(v_item.quote.lower().split())
                doc_quote_key = f"{v_item.doc_id}:{quote_key[:100]}"

                if doc_quote_key not in seen_quotes:
                    seen_quotes.add(doc_quote_key)
                    verified_evidence.append(v_item)
                else:
                    logger.debug(f"Skipping duplicate evidence from same doc: {v_item.quote[:50]}...")
            else:
                logger.warning(f"Rejected unverified quote: {item.get('quote', 'N/A')}")

        # 4. Handle Result
        if not verified_evidence:
            return {
                "answer": "Not found in the document.",
                "explanation": extraction_result.get("explanation", "No verified evidence found."),
                "sources": [],
                "abstained": True,
            }

        # 5. Synthesize Answer
        verified_dicts = [e.dict() for e in verified_evidence]
        final_answer = await self.llm.synthesize_answer(question, verified_dicts)

        return {
            "answer": final_answer,
            "sources": verified_dicts,
            "abstained": False,
            "explanation": extraction_result.get("explanation")
        }

    # ----------------------------
    # Query (Streaming / SSE)
    # ----------------------------
    async def query_stream(self, question: str, workspace_id: Optional[str] = None, messages: Optional[List[Dict]] = None, folder_path: Optional[str] = None):
        """Generator that yields SSE events: status updates, sources, and answer tokens."""
        workspace_id = normalize_workspace_id(workspace_id)

        # Conversational Rewrite
        if messages and len(messages) > 1:
            yield {"type": "status", "msg": "Contextualizing question..."}
            original_q = question
            question = await self.llm.rewrite_query(messages)

        # 1. Retrieval
        yield {"type": "status", "msg": f"Searching: {question}"}

        candidates = await self._retrieve_candidates(question, workspace_id, folder_path=folder_path)
        if not candidates:
            yield {"type": "status", "msg": "No relevant documents found."}
            yield {"type": "abstained", "explanation": "No matching documents found in workspace."}
            yield {"type": "done"}
            return

        # 2. Extraction
        yield {"type": "status", "msg": f"Analyzing {len(candidates)} candidates..."}

        evidence_windows = []
        for c in candidates:
            ws_id = c.get("workspace_id", "default")
            neighbors = self.store.fetch_neighbor_chunks(
                workspace_id=ws_id,
                doc_id=c["doc_id"],
                center_chunk_index=c["chunk_index"],
                window=2
            )
            full_text = "\n".join([n["text"] for n in neighbors])
            evidence_windows.append({
                "window_text": full_text,
                "doc_id": c["doc_id"],
                "chunk_ids": [n["chunk_id"] for n in neighbors],
                "center_chunk_id": c["chunk_id"],
                "chunks": neighbors
            })

        yield {"type": "status", "msg": "Extracting claims..."}

        if len(evidence_windows) <= 10:
            extraction_result = await self.llm.extract_evidence(question, evidence_windows)
        else:
            tasks = [self.llm.extract_evidence_single(question, w) for w in evidence_windows]
            results = await asyncio.gather(*tasks)
            combined_ev = []
            combined_expl = []
            for r in results:
                combined_ev.extend(r.get("evidence", []))
                if r.get("explanation"):
                    combined_expl.append(r["explanation"])
            extraction_result = {"evidence": combined_ev, "explanation": " | ".join(combined_expl)}

        raw_evidence = extraction_result["evidence"]

        if not raw_evidence:
            yield {"type": "status", "msg": "No evidence found to support answer."}
            yield {
                "type": "abstained",
                "explanation": extraction_result.get("explanation", "Documents were relevant but contained no answer.")
            }
            yield {"type": "done"}
            return

        # 3. Verification
        yield {"type": "status", "msg": f"Verifying {len(raw_evidence)} quotes (Strict Mode)..."}

        verified_evidence = []
        for item in raw_evidence:
            verified = self._verify_evidence_match(item, evidence_windows)
            if verified:
                verified_evidence.append(verified)

        if not verified_evidence:
            yield {"type": "status", "msg": "Verification failed. Low confidence."}
            yield {
                "type": "abstained",
                "explanation": "Potential answers were found but failed strict verification."
            }
            yield {"type": "done"}
            return

        # Merge adjacent chunks
        verified_evidence = self._merge_adjacent_evidence(verified_evidence)

        # 4. Yield Sources
        yield {"type": "status", "msg": "Synthesizing answer..."}
        verified_dicts = [e.dict() for e in verified_evidence]
        yield {"type": "sources", "data": verified_dicts}

        # 5. Stream Answer
        async for token in self.llm.synthesize_answer_stream(question, verified_dicts):
            yield {"type": "token", "text": token}

        yield {"type": "done"}

    # ----------------------------
    # Audit
    # ----------------------------
    async def run_audit(
        self,
        questions: List[Dict[str, Any]],
        workspace_id: str,
        folder_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Run an automated audit by executing multiple questions in parallel."""
        workspace_id = normalize_workspace_id(workspace_id)

        async def run_single_question(q_data: Dict[str, Any]) -> Dict[str, Any]:
            question_text = q_data["text"]
            severity = q_data.get("severity", "MEDIUM")
            category = q_data.get("category", "General")

            try:
                candidates = await self._retrieve_candidates(
                    question_text,
                    workspace_id,
                    folder_path=folder_path
                )

                if not candidates:
                    return {
                        "question": question_text,
                        "answer": "No relevant information found in the selected documents.",
                        "status": "NOT_FOUND",
                        "severity": severity,
                        "category": category,
                        "citations": []
                    }

                extraction_result = await self._extract_evidence_batched(question_text, candidates)
                verified_evidence = extraction_result.get("verified_evidence", [])

                if not verified_evidence:
                    return {
                        "question": question_text,
                        "answer": "Documents found but no specific answer could be extracted.",
                        "status": "UNCLEAR",
                        "severity": severity,
                        "category": category,
                        "citations": []
                    }

                verified_evidence = self._merge_adjacent_evidence(verified_evidence)
                verified_dicts = [e.dict() for e in verified_evidence]

                answer_tokens = []
                async for token in self.llm.synthesize_answer_stream(question_text, verified_dicts):
                    answer_tokens.append(token)
                answer_text = "".join(answer_tokens)

                citations = [
                    {
                        "doc_id": e["doc_id"],
                        "quote": e.get("quote", "")[:200],
                        "chunk_id": e.get("chunk_id")
                    }
                    for e in verified_dicts[:3]
                ]

                return {
                    "question": question_text,
                    "answer": answer_text,
                    "status": "FOUND",
                    "severity": severity,
                    "category": category,
                    "citations": citations
                }

            except Exception as e:
                logger.error(f"Audit question failed: {question_text[:50]}... - {e}")
                return {
                    "question": question_text,
                    "answer": f"Error processing question: {str(e)}",
                    "status": "ERROR",
                    "severity": severity,
                    "category": category,
                    "citations": []
                }

        tasks = [run_single_question(q) for q in questions]
        findings = await asyncio.gather(*tasks)
        return list(findings)

    # ----------------------------
    # Document Comparison
    # ----------------------------
    async def compare_documents(
        self,
        doc_id_a: str,
        doc_id_b: str,
        workspace_id: str
    ) -> Dict[str, Any]:
        """Compare two documents and identify material differences."""
        workspace_id = normalize_workspace_id(workspace_id)

        chunks_a = self.store.get_chunks_by_doc_id(workspace_id, doc_id_a)
        chunks_b = self.store.get_chunks_by_doc_id(workspace_id, doc_id_b)

        if not chunks_a:
            raise ValueError(f"Document A ({doc_id_a}) not found or has no content")
        if not chunks_b:
            raise ValueError(f"Document B ({doc_id_b}) not found or has no content")

        doc_a = self.store.get_document(workspace_id, doc_id_a)
        doc_b = self.store.get_document(workspace_id, doc_id_b)

        text_a = "\n\n".join([c["text"] for c in chunks_a])
        text_b = "\n\n".join([c["text"] for c in chunks_b])

        comparison_prompt = f"""You are a legal analyst comparing two versions of a document.

DOCUMENT A (Original):
---
{text_a[:15000]}
---

DOCUMENT B (Revised):
---
{text_b[:15000]}
---

Identify all MATERIAL differences between these documents. Focus on:
- Changes to legal terms, obligations, or rights
- Modified amounts, dates, or deadlines
- Added or removed clauses
- Changes to definitions
- Modified conditions or requirements

Ignore:
- Formatting or style changes
- Minor wording changes that don't affect meaning

For each difference, provide:
1. Category (e.g., "Financial Terms", "Termination", "Liability")
2. A clear description of what changed
3. Severity: HIGH (materially affects deal), MEDIUM (notable change), LOW (minor)
4. The original text snippet (brief)
5. The revised text snippet (brief)

Respond in JSON format:
{{
    "differences": [
        {{
            "category": "string",
            "description": "string",
            "severity": "HIGH" | "MEDIUM" | "LOW",
            "original_text": "string",
            "revised_text": "string"
        }}
    ],
    "summary": "1-2 sentence summary"
}}

If the documents are substantially identical, return an empty differences array.
Respond with ONLY valid JSON."""

        try:
            response = await self.llm.provider.complete_json(
                prompt=comparison_prompt,
                system="You are a legal document comparison expert."
            )

            if isinstance(response, str):
                import json as json_mod
                if response.startswith("```"):
                    response = response.split("```")[1]
                    if response.startswith("json"):
                        response = response[4:]
                comparison_result = json_mod.loads(response)
            else:
                comparison_result = response

            return {
                "doc_a": {
                    "doc_id": doc_id_a,
                    "title": doc_a.get("title", "Document A") if doc_a else "Document A",
                    "chunk_count": len(chunks_a)
                },
                "doc_b": {
                    "doc_id": doc_id_b,
                    "title": doc_b.get("title", "Document B") if doc_b else "Document B",
                    "chunk_count": len(chunks_b)
                },
                "differences": comparison_result.get("differences", []),
                "summary": comparison_result.get("summary", "No summary available"),
                "stats": {
                    "total_changes": len(comparison_result.get("differences", [])),
                    "high_severity": sum(1 for d in comparison_result.get("differences", []) if d.get("severity") == "HIGH"),
                    "medium_severity": sum(1 for d in comparison_result.get("differences", []) if d.get("severity") == "MEDIUM"),
                    "low_severity": sum(1 for d in comparison_result.get("differences", []) if d.get("severity") == "LOW")
                }
            }

        except Exception as e:
            logger.error(f"Failed to parse comparison result: {e}")
            return {
                "doc_a": {"doc_id": doc_id_a, "title": "Document A", "chunk_count": len(chunks_a)},
                "doc_b": {"doc_id": doc_id_b, "title": "Document B", "chunk_count": len(chunks_b)},
                "differences": [],
                "summary": "Comparison failed: Could not parse LLM response",
                "stats": {"total_changes": 0, "high_severity": 0, "medium_severity": 0, "low_severity": 0},
                "error": str(e)
            }


# ----------------------------
# CLI
# ----------------------------
def _print_query_result(out: Dict) -> None:
    print("\n" + "=" * 80)
    print("ANSWER")
    print("=" * 80)
    print(out["answer"].strip())

    print("\n" + "=" * 80)
    print("TOP SOURCES")
    print("=" * 80)

    if not out["sources"]:
        print("(none)")
    else:
        by_doc: Dict[str, List[Dict]] = {}
        for s in out["sources"]:
            by_doc.setdefault(s["doc_id"], []).append(s)

        for doc_id, items in by_doc.items():
            print(f"\nDOC: {doc_id}")
            for s in items[:5]:
                print(
                    f"  • {s.get('chunk_id', 'N/A')} | chars={s['start_char']}-{s['end_char']}"
                )
                print(f"    {clip_excerpt(s.get('quote', ''), 200)}")

    print("\n" + "=" * 80)
    print(f"ABSTAINED: {out['abstained']}")
    print("=" * 80)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Digital Filing Cabinet RAG Engine")
    parser.add_argument("--db", type=str, default="./lancedb_data", help="Path to LanceDB directory")

    sub = parser.add_subparsers(dest="cmd", required=True)

    ingest = sub.add_parser("ingest", help="Ingest a document")
    ingest.add_argument("--path", type=str, required=True)
    ingest.add_argument("--title", type=str, default=None)
    ingest.add_argument("--source", type=str, default="local")
    ingest.add_argument("--workspace", type=str, default=DEFAULT_WORKSPACE_ID)

    query_cmd = sub.add_parser("query", help="Ask a question")
    query_cmd.add_argument("--q", type=str, required=True)
    query_cmd.add_argument("--workspace", type=str, default=DEFAULT_WORKSPACE_ID)
    query_cmd.add_argument("--doc_id", type=str, default=None)
    query_cmd.add_argument("--doc_ids", type=str, default=None)

    rebuild = sub.add_parser("rebuild-bm25", help="Rebuild BM25 index")
    rebuild.add_argument("--workspace", type=str, default=DEFAULT_WORKSPACE_ID)

    args = parser.parse_args()

    cfg = Config.from_env(db_path=args.db)
    engine = RAGEngine(cfg)

    if args.cmd == "ingest":
        doc_id = asyncio.run(engine.ingest_text_file(
            args.path,
            title=args.title,
            source=args.source,
            workspace_id=args.workspace
        ))
        print(json.dumps({"status": "ok", "doc_id": doc_id, "workspace_id": args.workspace}, indent=2))

    elif args.cmd == "rebuild-bm25":
        engine.rebuild_bm25(workspace_id=args.workspace)
        print(json.dumps({"status": "ok", "workspace_id": args.workspace}, indent=2))

    elif args.cmd == "query":
        doc_ids_list = None
        if args.doc_ids:
            doc_ids_list = [d.strip() for d in args.doc_ids.split(",") if d.strip()]
        out = asyncio.run(engine.query(
            args.q,
            workspace_id=args.workspace,
            doc_id=args.doc_id,
            doc_ids=doc_ids_list
        ))
        _print_query_result(out)


if __name__ == "__main__":
    main()
