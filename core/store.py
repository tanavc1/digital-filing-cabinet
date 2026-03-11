"""
LanceDB vector storage with schema migration and workspace isolation.
"""
import os
import uuid
import logging
from typing import List, Dict, Optional, Any

import lancedb

from core.config import DEFAULT_WORKSPACE_ID
from core.utils import safe_mkdir, now_ts, _row_workspace_id


logger = logging.getLogger("rag_lancedb")


class LanceStore:
    """
    Manages LanceDB interactions for vector storage.
    Handles schema migration, document upserts, and vector search.
    Enforces strict workspace isolation using 'workspace_id'.
    """
    DOC_REQUIRED_FIELDS = [
        "doc_id", "workspace_id", "source", "uri", "title",
        "created_at", "modified_at", "content_hash",
        "summary_text", "summary_model", "summary_version",
        "folder_path",
        "doc_type",
        "risk_level"
    ]
    CHUNK_REQUIRED_FIELDS = [
        "chunk_id", "doc_id", "workspace_id", "source", "uri", "title",
        "chunk_index", "start_char", "end_char", "text",
        "chunk_type", "embedding", "created_at", "content_hash",
        "folder_path"
    ]
    CLAUSE_REQUIRED_FIELDS = [
        "id", "doc_id", "workspace_id", "clause_type", "extracted_value",
        "snippet", "confidence", "page_number", "created_at"
    ]
    ISSUE_REQUIRED_FIELDS = [
        "id", "doc_id", "workspace_id", "title", "description",
        "severity", "status", "owner", "action_required", "created_at"
    ]

    def __init__(self, db_path: str):
        safe_mkdir(db_path)
        self.db = lancedb.connect(db_path)

    def _table_field_names(self, table) -> List[str]:
        try:
            sch = table.schema
            try:
                return [f.name for f in sch]
            except Exception:
                return list(getattr(sch, "names", []))
        except Exception:
            try:
                return table.to_arrow().schema.names
            except Exception:
                return []

    def _ensure_table_schema(self, name: str, required_fields: List[str], defaults: Dict[str, Any]) -> None:
        """
        If the existing table is missing required fields, migrate it:
        - read all rows
        - add missing fields with defaults
        - drop + recreate table
        """
        try:
            table = self.db.open_table(name)
        except Exception:
            return

        existing_fields = set(self._table_field_names(table))
        missing = [f for f in required_fields if f not in existing_fields]
        if not missing:
            return

        logger.info(f"(migrate) '{name}' missing fields {missing}; performing table migration...")

        rows = table.to_arrow().to_pylist()
        migrated = []
        for r in rows:
            rr = dict(r)
            if "workspace_id" not in rr or not rr.get("workspace_id"):
                rr["workspace_id"] = DEFAULT_WORKSPACE_ID
            for k, v in defaults.items():
                if k not in rr:
                    rr[k] = v
            for f in missing:
                if f not in rr:
                    rr[f] = defaults.get(f)
            migrated.append(rr)

        try:
            self.db.drop_table(name)
        except Exception:
            try:
                self.db.delete_table(name)
            except Exception:
                pass

        if not migrated:
            seed = dict(defaults)
            seed["workspace_id"] = DEFAULT_WORKSPACE_ID
            if name == "documents":
                seed["doc_id"] = str(uuid.uuid4())
                seed["created_at"] = now_ts()
                seed["modified_at"] = now_ts()
                seed["content_hash"] = "seed"
                seed["source"] = "seed"
                seed["uri"] = ""
                seed["title"] = "seed"
                seed["summary_text"] = ""
                seed["summary_model"] = ""
                seed["summary_version"] = "v0"
            else:
                seed["chunk_id"] = f"seed_{uuid.uuid4()}"
                seed["doc_id"] = str(uuid.uuid4())
                seed["created_at"] = now_ts()
                seed["content_hash"] = "seed"
                seed["source"] = "seed"
                seed["uri"] = ""
                seed["title"] = "seed"
                seed["chunk_index"] = 0
                seed["start_char"] = 0
                seed["end_char"] = 0
                seed["text"] = ""
                seed["chunk_type"] = "discussion"
                seed["embedding"] = [0.0] * 384
            migrated = [seed]

        self.db.create_table(name, migrated)
        logger.info(f"(migrate) '{name}' migrated successfully.")

    def _open_or_create_table(self, name: str, rows: List[Dict]):
        # Schema migration for known tables
        if name == "documents":
            defaults = {
                "workspace_id": DEFAULT_WORKSPACE_ID,
                "source": "local", "uri": "", "title": "",
                "created_at": 0, "modified_at": 0, "content_hash": "",
                "summary_text": "", "summary_model": "", "summary_version": "v1",
                "folder_path": "/",
                "doc_type": "Unclassified",
                "risk_level": "Unknown",
            }
            self._ensure_table_schema(name, self.DOC_REQUIRED_FIELDS, defaults)
        elif name == "chunks":
            defaults = {
                "workspace_id": DEFAULT_WORKSPACE_ID,
                "source": "local", "uri": "", "title": "",
                "chunk_index": 0, "start_char": 0, "end_char": 0,
                "text": "", "chunk_type": "discussion",
                "embedding": [0.0] * 384,
                "created_at": 0, "content_hash": "",
                "folder_path": "/",
            }
            self._ensure_table_schema(name, self.CHUNK_REQUIRED_FIELDS, defaults)
        elif name == "clauses":
            defaults = {
                "workspace_id": DEFAULT_WORKSPACE_ID,
                "confidence": 0.0, "created_at": 0, "page_number": 0
            }
            self._ensure_table_schema(name, self.CLAUSE_REQUIRED_FIELDS, defaults)
        elif name == "issues":
            defaults = {
                "workspace_id": DEFAULT_WORKSPACE_ID,
                "status": "open", "severity": "info", "created_at": 0
            }
            self._ensure_table_schema(name, self.ISSUE_REQUIRED_FIELDS, defaults)

        try:
            return self.db.open_table(name)
        except Exception:
            return self.db.create_table(name, rows)

    def _get_table_secure(self, name: str):
        """Safely get table or return None if not exists."""
        try:
            return self.db.open_table(name)
        except Exception:
            return None

    # ----------------------------
    # Documents
    # ----------------------------
    def upsert_document(self, doc_row: Dict) -> None:
        ws = doc_row.get("workspace_id") or DEFAULT_WORKSPACE_ID
        docs_table = self._open_or_create_table("documents", [doc_row])
        docs_table.delete(f"doc_id = '{doc_row['doc_id']}' AND workspace_id = '{ws}'")
        docs_table.add([doc_row])

    def list_documents(self, workspace_id: str) -> List[Dict]:
        table = self._get_table_secure("documents")
        if not table:
            return []
        try:
            out = table.search().where(
                f"workspace_id = '{workspace_id}'", prefilter=True
            ).limit(100_000).to_list()
        except Exception:
            # Fallback for tables without vector column
            rows = table.to_arrow().to_pylist()
            out = [r for r in rows if _row_workspace_id(r) == workspace_id]
        out.sort(key=lambda r: r.get("created_at", 0), reverse=True)
        return out

    def delete_document(self, workspace_id: str, doc_id: str) -> bool:
        logger.info(f"Deleting doc {doc_id} from workspace {workspace_id}")
        deleted_any = False
        try:
            docs = self.db.open_table("documents")
            docs.delete(f"doc_id = '{doc_id}' AND workspace_id = '{workspace_id}'")
            deleted_any = True
            logger.info(f"Deleted from documents table: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to delete from documents table: {e}")

        try:
            chunks = self.db.open_table("chunks")
            chunks.delete(f"doc_id = '{doc_id}' AND workspace_id = '{workspace_id}'")
            logger.info(f"Deleted from chunks table: {doc_id}")
            deleted_any = True
        except Exception as e:
            logger.error(f"Failed to delete from chunks table: {e}")

        return deleted_any

    def fetch_document(self, workspace_id: str, doc_id: str) -> Optional[Dict]:
        table = self._get_table_secure("documents")
        if not table:
            return None
        try:
            rows = table.search().where(
                f"doc_id = '{doc_id}' AND workspace_id = '{workspace_id}'",
                prefilter=True
            ).limit(1).to_list()
            return rows[0] if rows else None
        except Exception:
            docs = self.fetch_documents_by_ids(workspace_id, [doc_id])
            return docs.get(doc_id)

    def fetch_documents_by_ids(self, workspace_id: str, doc_ids: List[str]) -> Dict[str, Dict]:
        if not doc_ids:
            return {}
        table = self._get_table_secure("documents")
        if not table:
            return {}
        try:
            id_list = ", ".join(f"'{d}'" for d in doc_ids)
            rows = table.search().where(
                f"workspace_id = '{workspace_id}' AND doc_id IN ({id_list})",
                prefilter=True
            ).limit(len(doc_ids)).to_list()
            return {r["doc_id"]: r for r in rows}
        except Exception:
            # Fallback
            rows = table.to_arrow().to_pylist()
            wanted = set(doc_ids)
            out = {}
            for r in rows:
                if _row_workspace_id(r) != workspace_id:
                    continue
                if r.get("doc_id") in wanted:
                    out[r["doc_id"]] = r
            return out

    def fetch_document_by_content_hash(self, workspace_id: str, content_hash: str) -> Optional[Dict]:
        table = self._get_table_secure("documents")
        if not table:
            return None
        try:
            rows = table.search().where(
                f"workspace_id = '{workspace_id}' AND content_hash = '{content_hash}'",
                prefilter=True
            ).limit(1).to_list()
            return rows[0] if rows else None
        except Exception:
            rows = table.to_arrow().to_pylist()
            for r in rows:
                if _row_workspace_id(r) != workspace_id:
                    continue
                if r.get("content_hash") == content_hash:
                    return r
            return None

    # ----------------------------
    # Chunks
    # ----------------------------
    def upsert_chunks(self, chunk_rows: List[Dict]) -> None:
        if not chunk_rows:
            return
        chunks_table = self._open_or_create_table("chunks", chunk_rows[:1])
        doc_id = chunk_rows[0]["doc_id"]
        ws = chunk_rows[0].get("workspace_id") or DEFAULT_WORKSPACE_ID

        chunks_table.delete(f"doc_id = '{doc_id}' AND workspace_id = '{ws}'")
        chunks_table.add(chunk_rows)

        try:
            chunks_table.create_index("embedding")
        except Exception as e:
            logger.info(f"(ok) vector index not created / already exists / not supported: {e}")

    def fetch_chunks_for_doc(self, workspace_id: str, doc_id: str) -> List[Dict]:
        """Retrieve all chunks for a document, sorted by index."""
        table = self._get_table_secure("chunks")
        if not table:
            return []
        try:
            out = table.search().where(
                f"doc_id = '{doc_id}' AND workspace_id = '{workspace_id}'",
                prefilter=True
            ).limit(10_000).to_list()
            out.sort(key=lambda x: x.get("chunk_index", 0))
            return out
        except Exception as e:
            logger.error(f"Fetch chunks failed for {doc_id}: {e}")
            return []

    def vector_search(
        self,
        query_vec: List[float],
        limit: int,
        workspace_id: str,
        doc_ids: Optional[List[str]] = None,
    ) -> List[Dict]:
        table = self.db.open_table("chunks")
        where_clause = f"workspace_id = '{workspace_id}'"
        if doc_ids:
            id_list = ", ".join(f"'{d}'" for d in doc_ids)
            where_clause += f" AND doc_id IN ({id_list})"
        try:
            return table.search(query_vec).where(
                where_clause, prefilter=True
            ).limit(limit).to_list()
        except Exception:
            # Fallback: post-filter
            oversample = max(limit * 5, 50)
            raw = table.search(query_vec).limit(oversample).to_list()
            wanted = set(doc_ids) if doc_ids else None
            out = []
            for r in raw:
                if _row_workspace_id(r) != workspace_id:
                    continue
                if wanted is not None and r.get("doc_id") not in wanted:
                    continue
                out.append(r)
                if len(out) >= limit:
                    break
            return out

    def load_all_chunks_minimal(self, workspace_id: Optional[str] = None) -> List[Dict]:
        table = self.db.open_table("chunks")
        try:
            if workspace_id:
                rows = table.search().where(
                    f"workspace_id = '{workspace_id}'", prefilter=True
                ).limit(500_000).to_list()
            else:
                rows = table.to_arrow().to_pylist()
        except Exception:
            rows = table.to_arrow().to_pylist()
            if workspace_id:
                rows = [r for r in rows if _row_workspace_id(r) == workspace_id]
        out = []
        for r in rows:
            out.append({
                "chunk_id": r["chunk_id"],
                "doc_id": r["doc_id"],
                "workspace_id": r.get("workspace_id") or DEFAULT_WORKSPACE_ID,
                "chunk_index": r["chunk_index"],
                "start_char": r["start_char"],
                "end_char": r["end_char"],
                "text": r["text"],
                "chunk_type": r.get("chunk_type", "discussion"),
            })
        return out

    def fetch_neighbor_chunks(self, workspace_id: str, doc_id: str, center_chunk_index: int, window: int = 1) -> List[Dict]:
        """
        Retrieves the center chunk plus 'window' chunks before and after,
        strictly within the same document and workspace.
        """
        table = self.db.open_table("chunks")
        min_idx = center_chunk_index - window
        max_idx = center_chunk_index + window

        try:
            candidates = table.search().where(
                f"doc_id = '{doc_id}' AND workspace_id = '{workspace_id}' "
                f"AND chunk_index >= {min_idx} AND chunk_index <= {max_idx}",
                prefilter=True
            ).limit(2 * window + 1).to_list()
        except Exception:
            # Fallback
            rows = table.to_arrow().to_pylist()
            candidates = [
                r for r in rows
                if _row_workspace_id(r) == workspace_id
                and r["doc_id"] == doc_id
                and min_idx <= int(r["chunk_index"]) <= max_idx
            ]

        candidates.sort(key=lambda x: x["chunk_index"])
        return candidates

    def get_chunks_by_doc_id(self, workspace_id: str, doc_id: str) -> List[Dict]:
        """
        Get all chunks for a specific document, ordered by chunk_index.
        Used for document comparison and full-text retrieval.
        """
        try:
            table = self.db.open_table("chunks")
        except Exception:
            return []

        try:
            rows = table.search().where(
                f"doc_id = '{doc_id}' AND workspace_id = '{workspace_id}'",
                prefilter=True
            ).limit(10_000).to_list()
        except Exception:
            rows = table.to_arrow().to_pylist()
            rows = [
                r for r in rows
                if _row_workspace_id(r) == workspace_id and r.get("doc_id") == doc_id
            ]

        chunks = []
        for r in rows:
            chunks.append({
                "chunk_id": r["chunk_id"],
                "doc_id": r["doc_id"],
                "workspace_id": r.get("workspace_id") or DEFAULT_WORKSPACE_ID,
                "chunk_index": r["chunk_index"],
                "start_char": r["start_char"],
                "end_char": r["end_char"],
                "text": r["text"],
                "chunk_type": r.get("chunk_type", "discussion"),
            })

        chunks.sort(key=lambda x: x["chunk_index"])
        return chunks

    def get_document(self, workspace_id: str, doc_id: str) -> Optional[Dict]:
        """Deprecated: use fetch_document() instead."""
        return self.fetch_document(workspace_id, doc_id)

    # ----------------------------
    # Clauses & Issues
    # ----------------------------
    def upsert_clauses(self, rows: List[Dict]) -> None:
        if not rows:
            return
        self._open_or_create_table("clauses", rows)
        table = self.db.open_table("clauses")
        for r in rows:
            cid = r["id"]
            try:
                table.delete(f"id = '{cid}'")
            except Exception:
                pass
        table.add(rows)

    def upsert_clause(self, row: Dict) -> None:
        """Upsert a single clause."""
        self.upsert_clauses([row])

    def list_clauses(self, workspace_id: str) -> List[Dict]:
        table = self._get_table_secure("clauses")
        if not table:
            return []
        try:
            return table.search().where(
                f"workspace_id = '{workspace_id}'", prefilter=True
            ).limit(100_000).to_list()
        except Exception:
            rows = table.to_arrow().to_pylist()
            return [r for r in rows if _row_workspace_id(r) == workspace_id]

    def upsert_issue(self, row: Dict) -> None:
        table = self._open_or_create_table("issues", [row])
        try:
            table.delete(f"id = '{row['id']}'")
        except Exception:
            pass
        table.add([row])

    def upsert_issues(self, rows: List[Dict]) -> None:
        """Upsert multiple issues."""
        if not rows:
            return
        self._open_or_create_table("issues", rows)
        table = self.db.open_table("issues")
        for r in rows:
            try:
                table.delete(f"id = '{r['id']}'")
            except Exception:
                pass
        table.add(rows)

    def delete_issue(self, issue_id: str) -> None:
        try:
            table = self.db.open_table("issues")
            table.delete(f"id = '{issue_id}'")
        except Exception:
            pass

    def list_issues(self, workspace_id: str) -> List[Dict]:
        table = self._get_table_secure("issues")
        if not table:
            return []
        try:
            return table.search().where(
                f"workspace_id = '{workspace_id}'", prefilter=True
            ).limit(100_000).to_list()
        except Exception:
            rows = table.to_arrow().to_pylist()
            return [r for r in rows if _row_workspace_id(r) == workspace_id]
