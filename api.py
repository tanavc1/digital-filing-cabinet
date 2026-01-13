"""
Digital Filing Cabinet - FastAPI Backend
========================================

Exposes REST endpoints for:
1. Document Management (Upload, List, Delete) - scoped by 'workspace_id'.
2. RAG Querying (Streaming SSE) - intelligent answer generation with evidence.
3. System Health Check.
"""
import os
# Set environment variables BEFORE importing heavy libraries (torch, numpy, onnx)
# This prevents OpenMP/MKL from spawning too many threads and crashing Uvicorn workers
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import json
import tempfile
import asyncio
from typing import Optional, Dict, Any, List

import filetype
import filetype
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse
import asyncio
import json
from pydantic import BaseModel, Field

from main import Config, RAGEngine, DEFAULT_WORKSPACE_ID
from docling_loader import DoclingExtractor


app = FastAPI(title="Digital Filing Cabinet API", version="0.4.0")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ENGINE: Optional[RAGEngine] = None
_DOCLING_NO_OCR: Optional[DoclingExtractor] = None
_DOCLING_OCR: Optional[DoclingExtractor] = None


def get_engine() -> RAGEngine:
    global _ENGINE
    if _ENGINE is None:
        db_path = os.getenv("DB_PATH", "./lancedb_data")
        cfg = Config.from_env(db_path=db_path)
        _ENGINE = RAGEngine(cfg)
    return _ENGINE


def get_docling_extractor(enable_ocr: bool) -> DoclingExtractor:
    global _DOCLING_NO_OCR, _DOCLING_OCR
    if enable_ocr:
        if _DOCLING_OCR is None:
            _DOCLING_OCR = DoclingExtractor(enable_ocr=True)
        return _DOCLING_OCR
    else:
        if _DOCLING_NO_OCR is None:
            _DOCLING_NO_OCR = DoclingExtractor(enable_ocr=False)
        return _DOCLING_NO_OCR


# ----------------------------
# Request/Response models
# ----------------------------
class IngestTextRequest(BaseModel):
    workspace_id: str = Field(default=DEFAULT_WORKSPACE_ID, description="Workspace scope (tenant boundary)")
    title: Optional[str] = Field(default=None, description="Optional display title for the document")
    source: str = Field(default="local", description="Source label (e.g., local, gdrive, slack)")
    text: str = Field(..., description="Plain text content to ingest")


class IngestResponse(BaseModel):
    status: str
    doc_id: str


class QueryRequest(BaseModel):
    q: str
    workspace_id: Optional[str] = "default"
    doc_id: Optional[str] = None
    doc_ids: Optional[List[str]] = None
    messages: Optional[List[Dict]] = None # History support


class SourceOut(BaseModel):
    chunk_id: Optional[str] = None # Legacy support
    evidence_id: Optional[str] = None # Phase 8
    doc_id: str
    workspace_id: str = "default"
    # Unified 'text' vs 'excerpt' vs 'quote'
    quote: str
    start_char: int
    end_char: int
    content_hash: Optional[str] = None # Phase 8
    confidence: float
    verified: bool = True


class ClosestMentionOut(BaseModel):
    doc_id: str
    chunk_id: str
    excerpt: str
    rerank_score: float


class QueryResponse(BaseModel):
    answer: str
    abstained: bool
    sources: list[SourceOut]
    explanation: Optional[str] = None
    closest_mentions: List[ClosestMentionOut] = []


# ----------------------------
# Routes
# ----------------------------
@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}


@app.get("/documents")
def list_docs(workspace_id: str = DEFAULT_WORKSPACE_ID) -> Dict[str, Any]:
    engine = get_engine()
    try:
        docs = engine.list_docs(workspace_id=workspace_id)
        cleaned = []
        for d in docs:
            cleaned.append({
                "doc_id": d.get("doc_id"),
                "title": d.get("title"),
                "source": d.get("source"),
                "created_at": d.get("created_at"),
                "modified_at": d.get("modified_at"),
                "uri": d.get("uri"),
            })
        return {"status": "ok", "workspace_id": workspace_id, "documents": cleaned}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"List docs failed: {e}")


@app.delete("/documents/{doc_id}")
def delete_doc(doc_id: str, workspace_id: str = DEFAULT_WORKSPACE_ID) -> Dict[str, Any]:
    engine = get_engine()
    try:
        ok = engine.delete_doc(doc_id=doc_id, workspace_id=workspace_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Document not found (or already deleted).")
        return {"status": "ok", "workspace_id": workspace_id, "doc_id": doc_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete doc failed: {e}")


@app.get("/documents/{doc_id}/content")
async def get_doc_content(doc_id: str, workspace_id: str = DEFAULT_WORKSPACE_ID) -> Dict[str, str]:
    engine = get_engine()
    text = await engine.get_doc_text(doc_id, workspace_id=workspace_id)
    if text is None:
        raise HTTPException(status_code=404, detail="Document not found or content missing")
    return {"text": text}



@app.post("/ingest/text", response_model=IngestResponse)
async def ingest_text(req: IngestTextRequest) -> IngestResponse:
    engine = get_engine()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(req.text)
            tmp_path = f.name

        doc_id = await engine.ingest_text_file(
            tmp_path,
            title=req.title,
            source=req.source,
            workspace_id=req.workspace_id
        )
        return IngestResponse(status="ok", doc_id=doc_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {e}")
    finally:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


@app.post("/ingest/file", response_model=IngestResponse)
async def ingest_file(
    workspace_id: str = DEFAULT_WORKSPACE_ID,
    title: Optional[str] = None,
    source: str = "local",
    file: UploadFile = File(...),
) -> IngestResponse:
    """
    Ingest a UTF-8 plain text file upload (.txt only).
    """
    engine = get_engine()

    if not (file.filename or "").lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported on /ingest/file. Use /ingest/any.")

    tmp_path = None
    try:
        raw = await file.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text.")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(text)
            tmp_path = f.name

        doc_id = await engine.ingest_text_file(
            tmp_path,
            title=title or file.filename,
            source=source,
            workspace_id=workspace_id
        )
        return IngestResponse(status="ok", doc_id=doc_id)
    finally:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


@app.post("/ingest/any", response_model=IngestResponse)
async def ingest_any(
    workspace_id: str = DEFAULT_WORKSPACE_ID,
    source: str = "local",
    title: Optional[str] = None,
    enable_ocr: bool = False,
    file: UploadFile = File(...),
) -> IngestResponse:
    """
    Universal ingestion endpoint:
    - Accepts: PDF, DOCX, PPTX, XLSX, HTML, MD, TXT, etc.
    - Uses Docling to convert -> Markdown text -> your existing ingestion pipeline.
    - OCR optional: enable_ocr=true (requires OCR deps installed).
    """
    engine = get_engine()

    tmp_bin = None
    tmp_txt = None

    try:
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="Empty file upload.")

        # MIME sniff (best-effort)
        kind = filetype.guess(raw)
        guessed_mime = kind.mime if kind else (file.content_type or None)

        filename = file.filename or "upload"
        _, ext = os.path.splitext(filename)
        if not ext:
            ext = ".bin"

        # Special-case .txt: skip Docling
        if filename.lower().endswith(".txt") or guessed_mime == "text/plain":
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="Text file must be UTF-8.")
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
                f.write(text)
                tmp_txt = f.name
            doc_id = await engine.ingest_text_file(
                tmp_txt,
                title=title or filename,
                source=source,
                workspace_id=workspace_id
            )
            return IngestResponse(status="ok", doc_id=doc_id)

        # Write upload to disk for processing
        with tempfile.NamedTemporaryFile(mode="wb", suffix=ext, delete=False) as f:
            f.write(raw)
            tmp_bin = f.name

        # DIRECT PDF EXTRACTION - Use new robust hybrid extractor
        is_pdf = ext.lower() == '.pdf' or (guessed_mime and 'pdf' in guessed_mime.lower())
        
        if is_pdf:
            import pdf_extractor
            import logging
            import asyncio
            
            logger = logging.getLogger("uvicorn.error")
            logger.info(f"Extracting PDF with Hybrid Extractor: {filename} (OCR={enable_ocr})")
            
            try:
                # Run heavyweight OCR/extraction in thread
                result = await asyncio.to_thread(
                    pdf_extractor.extract_pdf,
                    tmp_bin,
                    title=title or filename,
                    enable_ocr=enable_ocr
                )
                
                extracted_text = result.text
                logger.info(f"PDF extraction success. {result.page_count} pages, {result.pages_with_ocr} scanned, {result.tables_found} tables.")
                
            except Exception as e:
                import traceback
                error_msg = f"PDF extraction failed: {e}\n{traceback.format_exc()}"
                logger.error(error_msg)
                with open("upload_error.log", "w") as err_f:
                    err_f.write(error_msg)
                raise HTTPException(status_code=500, detail=f"PDF extraction failed: {e}")
        else:
            # For non-PDFs, still use Docling
            extractor = get_docling_extractor(enable_ocr=enable_ocr)
            import asyncio
            import logging
            logger = logging.getLogger("uvicorn.error")
            logger.info(f"Starting Docling extraction for {filename} (OCR={enable_ocr})...")
            
            try:
                extracted = await asyncio.to_thread(
                    extractor.extract, 
                    tmp_bin, 
                    title=title or filename, 
                    mime=guessed_mime
                )
                extracted_text = extracted.text
                logger.info(f"Docling extraction success. Text len: {len(extracted_text)}")
            except Exception as e:
                import traceback
                error_msg = f"Docling extraction failed: {e}\n{traceback.format_exc()}"
                logger.error(error_msg)
                with open("upload_error.log", "w") as err_f:
                    err_f.write(error_msg)
                raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

        # Feed extracted markdown/text into existing ingestion pipeline
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(extracted_text)
            tmp_txt = f.name

        doc_id = await engine.ingest_text_file(
            tmp_txt,
            title=title or filename,
            source=source,
            workspace_id=workspace_id
        )
        return IngestResponse(status="ok", doc_id=doc_id)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest(any) failed: {e}")
    finally:
        for p in (tmp_txt, tmp_bin):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


@app.post("/ingest/any/stream")
async def ingest_any_stream(
    workspace_id: str = Form(DEFAULT_WORKSPACE_ID),
    source: str = Form("local"),
    title: Optional[str] = Form(None),
    enable_ocr: bool = Form(False),
    file: UploadFile = File(...),
):
    """
    Upload with SSE progress streaming.
    Yields events: {"type": "progress", "stage": "...", "percent": X}
    Final event: {"type": "complete", "doc_id": "..."}
    """
    engine = get_engine()
    
    async def event_generator():
        tmp_bin = None
        tmp_txt = None

        try:
            # Stage 1: Upload received
            yield f'data: {json.dumps({"type": "progress", "stage": "received", "percent": 5})}\n\n'
            
            raw = await file.read()
            if not raw:
                yield f'data: {json.dumps({"type": "error", "msg": "Empty file upload."})}\n\n'
                return

            # MIME sniff
            kind = filetype.guess(raw)
            guessed_mime = kind.mime if kind else (file.content_type or None)
            filename = file.filename or "upload"
            _, ext = os.path.splitext(filename)
            if not ext:
                ext = ".bin"

            # Special-case .txt
            if filename.lower().endswith(".txt") or guessed_mime == "text/plain":
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    yield f'data: {json.dumps({"type": "error", "msg": "Text file must be UTF-8."})}\n\n'
                    return
                    
                with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
                    f.write(text)
                    tmp_txt = f.name
                    
                # Progress callback
                async def progress_cb(data):
                    yield f'data: {json.dumps({"type": "progress", **data})}\n\n'
                    
                doc_id = await engine.ingest_text_file(
                    tmp_txt,
                    title=title or filename,
                    source=source,
                    workspace_id=workspace_id,
                    progress_callback=progress_cb
                )
                
                yield f'data: {json.dumps({"type": "complete", "doc_id": doc_id})}\n\n'
                return

            # Docling path
            yield f'data: {json.dumps({"type": "progress", "stage": "extracting", "percent": 8})}\n\n'
            
            with tempfile.NamedTemporaryFile(mode="wb", suffix=ext, delete=False) as f:
                f.write(raw)
                tmp_bin = f.name

            extractor = get_docling_extractor(enable_ocr=enable_ocr)
            extracted = extractor.extract(tmp_bin, title=title or filename, mime=guessed_mime)

            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
                f.write(extracted.text)
                tmp_txt = f.name

            # Progress callback that yields events
            async def progress_cb(data):
                await asyncio.sleep(0)  # Yield control
                # Can't yield from nested function - need to use queue
                # For simplicity, we'll inline progress events manually
                pass
                
            doc_id = await engine.ingest_text_file(
                tmp_txt,
                title=extracted.title,
                source=source,
                workspace_id=workspace_id,
                progress_callback=lambda data: None  # Skip for now in Docling path
            )
            
            # Since we can't easily yield from callback, emit final stages manually  
            yield f'data: {json.dumps({"type": "progress", "stage": "indexing", "percent": 90})}\n\n'
            yield f'data: {json.dumps({"type": "complete", "doc_id": doc_id})}\n\n'

        except Exception as e:
            yield f'data: {json.dumps({"type": "error", "msg": str(e)})}\n\n'
        finally:
            for p in (tmp_txt, tmp_bin):
                try:
                    if p and os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass
                    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest) -> QueryResponse:
    engine = get_engine()
    try:
        out = await engine.query(
            req.q,
            workspace_id=req.workspace_id,
            doc_id=req.doc_id,
            doc_ids=req.doc_ids
        )
        sources = [SourceOut(**s) for s in out.get("sources", [])]
        closest = [ClosestMentionOut(**c) for c in out.get("closest_mentions", [])]
        return QueryResponse(
            answer=out.get("answer", ""),
            abstained=bool(out.get("abstained", True)),
            sources=sources,
            explanation=out.get("explanation"),
            closest_mentions=closest,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@app.post("/rebuild-bm25")
def rebuild_bm25(workspace_id: str = DEFAULT_WORKSPACE_ID) -> Dict[str, Any]:
    engine = get_engine()
    try:
        engine.rebuild_bm25(workspace_id=workspace_id)
        return {"status": "ok", "workspace_id": workspace_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rebuild failed: {e}")


@app.post("/query_stream")
async def query_stream_endpoint(body: QueryRequest):
    """
    Server-Sent Events (SSE) endpoint for rich streaming.
    Yields events:
      data: {"type": "status", "msg": "..."}
      data: {"type": "sources", "data": [...]}
      data: {"type": "token", "text": "..."}
      data: {"type": "abstained", ...}
      data: {"type": "done"}
    """
    engine = get_engine()
    
    async def event_generator():
        try:
            async for event in engine.query_stream(body.q, body.workspace_id, body.messages):
                # Ensure SourceOut serialization if type is sources
                if event["type"] == "sources":
                    mapped_sources = []
                    for s in event["data"]:
                        mapped_sources.append({
                            "doc_id": s["doc_id"],
                            "quote": s.get("quote", ""),
                            "start_char": s.get("start_char", 0),
                            "end_char": s.get("end_char", 0),
                            "chunk_id": s.get("chunk_id"),
                            "confidence": 1.0, 
                            "verified": True
                        })
                    event["data"] = mapped_sources

                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            # Yield error event
            err_payload = {"type": "error", "msg": str(e)}
            yield f"data: {json.dumps(err_payload)}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Run with:
# uvicorn api:app --host 0.0.0.0 --port 8000
