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
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

import filetype
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from main import Config, RAGEngine, DEFAULT_WORKSPACE_ID
from docling_loader import DoclingExtractor

# Production-grade logging
logger = logging.getLogger("api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# Rate limiter (10 queries per minute per IP)
limiter = Limiter(key_func=get_remote_address)



app = FastAPI(title="Digital Filing Cabinet API", version="0.5.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from fastapi.middleware.cors import CORSMiddleware

# Environment-based CORS (permissive in dev, configurable in prod)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    """
    Optional API Key verification.
    If API_SECRET is set in .env, all non-public endpoints require 'X-API-Key' header.
    """
    # 1. Allow Public Endpoints
    if request.url.path in ["/", "/health", "/docs", "/openapi.json", "/redoc"]:
        return await call_next(request)
        
    # 2. Allow CORS Preflight
    if request.method == "OPTIONS":
        return await call_next(request)

    # 3. Check Secret
    secret = os.getenv("API_SECRET")
    if not secret:
        # Development mode (no secret set)
        return await call_next(request)
        
    # 4. Verify Header
    client_key = request.headers.get("x-api-key")
    if client_key != secret:
        logger.warning(f"Unauthorized access attempt from {request.client.host}")
        return StreamingResponse(content=iter(["Unauthorized"]), status_code=401)
        
    return await call_next(request)


@app.on_event("startup")
async def startup_validation():
    """Validate environment on startup."""
    required_vars = ["OPENAI_API_KEY"]
    missing = [k for k in required_vars if not os.getenv(k)]
    if missing:
        logger.error(f"Missing required environment variables: {missing}")
        raise RuntimeError(f"Missing required env vars: {missing}")
    
    logger.info("Environment validated. Server ready.")
    
    # Start background pre-warming
    asyncio.create_task(background_warmup())

async def background_warmup():
    """Pre-warm the RAG engine in the background."""
    logger.info("Starting background engine pre-warm...")
    try:
        # Run in thread pool to avoid blocking event loop
        await asyncio.to_thread(get_engine)
        logger.info("Engine pre-warmed successfully in background.")
    except Exception as e:
        logger.warning(f"Background pre-warm failed: {e}")


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
    """Enhanced health check for monitoring systems."""
    return {
        "status": "healthy",
        "version": "0.5.0",
        "engine_loaded": _ENGINE is not None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


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
        logger.error(f"List docs failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document list.")


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
        logger.error(f"Delete doc failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document.")


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
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail="Document ingestion failed. Please verify the file format.")
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

            raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text.")
        
        # PERSISTENCE CHANGE: Save to ./data/uploads instead of temp
        file_id = str(uuid.uuid4())
        upload_dir = os.path.join(os.getenv("UPLOAD_DIR", "./data/uploads"), workspace_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        safe_name = os.path.basename(file.filename) or "upload.txt"
        perm_path = os.path.join(upload_dir, f"{file_id}_{safe_name}")
        
        with open(perm_path, "w", encoding="utf-8") as f:
            f.write(text)

        doc_id = await engine.ingest_text_file(
            perm_path,
            title=title or file.filename,
            source=source,
            workspace_id=workspace_id,
            uri=perm_path # Persistent URI
        )
        return IngestResponse(status="ok", doc_id=doc_id)
    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper for persistent saving
async def save_upload_to_disk(file: UploadFile, workspace_id: str) -> str:
    """Save upload to persistent storage and return absolute path."""
    upload_dir = os.path.join(os.getenv("UPLOAD_DIR", "./data/uploads"), workspace_id)
    os.makedirs(upload_dir, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    filename = os.path.basename(file.filename or "unknown")
    perm_path = os.path.join(upload_dir, f"{file_id}_{filename}")
    
    with open(perm_path, "wb") as f:
        while content := await file.read(1024 * 1024): # 1MB chunks
            f.write(content)
            
    return perm_path

@app.post("/ingest/any", response_model=IngestResponse)
async def ingest_any(
    workspace_id: str = DEFAULT_WORKSPACE_ID,
    source: str = "local",
    title: Optional[str] = None,
    enable_ocr: bool = False,
    enable_vision: bool = False,
    file: UploadFile = File(...),
) -> IngestResponse:
    """
    Universal ingestion endpoint:
    - Accepts: PDF, DOCX, PPTX, XLSX, HTML, MD, TXT, etc.
    - Uses Docling to convert -> Markdown text -> your existing ingestion pipeline.
    - OCR optional: enable_ocr=true (requires OCR deps installed).
    - Vision optional: enable_vision=true (uses Gemini to analyze images in PDFs).
    """
    engine = get_engine()

    try:
        # 1. Save Original to Disk (Persistent)
        perm_bin_path = await save_upload_to_disk(file, workspace_id)
        filename = file.filename or "upload"
        
        # MIME sniff
        kind = filetype.guess(perm_bin_path)
        guessed_mime = kind.mime if kind else (file.content_type or None)
        _, ext = os.path.splitext(filename)

        # 2. Extract Content
        # Special-case .txt
        if filename.lower().endswith(".txt") or guessed_mime == "text/plain":
            with open(perm_bin_path, "r", encoding="utf-8") as f:
                extracted_text = f.read()
        else:
            # DIRECT PDF EXTRACTION
            is_pdf = ext.lower() == '.pdf' or (guessed_mime and 'pdf' in guessed_mime.lower())
            
            if is_pdf:
                import pdf_extractor
                import logging
                import asyncio
                
                logger = logging.getLogger("uvicorn.error")
                logger.info(f"Extracting Persistent PDF: {perm_bin_path} (OCR={enable_ocr}, Vision={enable_vision})")
                
                try:
                    result = await asyncio.to_thread(
                        pdf_extractor.extract_pdf,
                        perm_bin_path, # Use persistent path
                        title=title or filename,
                        enable_ocr=enable_ocr,
                        enable_vision=enable_vision
                    )
                    extracted_text = result.text
                except Exception as e:
                    import traceback
                    logger.error(f"PDF extraction failed: {e}")
                    raise HTTPException(status_code=500, detail="PDF extraction failed. File may be corrupted.")
            else:
                # Docling
                extractor = get_docling_extractor(enable_ocr=enable_ocr)
                import asyncio
                import logging
                logger = logging.getLogger("uvicorn.error")
                logger.info(f"Starting Persistent Docling extraction for {filename}...")
                
                try:
                    extracted = await asyncio.to_thread(
                        extractor.extract, 
                        perm_bin_path, 
                        title=title or filename, 
                        mime=guessed_mime
                    )
                    extracted_text = extracted.text
                except Exception as e:
                    logger.error(f"Docling extraction failed: {e}")
                    raise HTTPException(status_code=500, detail="Content extraction failed.")

        # 3. Save Extracted Markdown (Persistent)
        perm_md_path = perm_bin_path + ".md"
        with open(perm_md_path, "w", encoding="utf-8") as f:
            f.write(extracted_text)

        # 4. Ingest (Source=MD, URI=Original Binary)
        doc_id = await engine.ingest_text_file(
            perm_md_path,
            title=title or filename,
            source=source,
            workspace_id=workspace_id,
            uri=perm_bin_path # Point to the original file
        )
        return IngestResponse(status="ok", doc_id=doc_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingest(any) persistent failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/image", response_model=IngestResponse)
async def ingest_image(
    workspace_id: str = DEFAULT_WORKSPACE_ID,
    source: str = "local",
    title: Optional[str] = None,
    file: UploadFile = File(...),
) -> IngestResponse:
    """
    Direct image ingestion endpoint.
    - Accepts: PNG, JPG, GIF, WebP, etc.
    - Uses Gemini Vision to analyze the image content.
    - Creates a searchable text document from the analysis.
    """
    import logging
    from vision_analyzer import analyze_image, analyze_document_image
    
    logger = logging.getLogger("uvicorn.error")
    engine = get_engine()
    
    try:
        # 1. Save Original Image (Persistent)
        perm_img_path = await save_upload_to_disk(file, workspace_id)
        filename = file.filename or "image"
        
        # Validate it's an image
        kind = filetype.guess(perm_img_path)
        if not kind or not kind.mime.startswith("image/"):
            raise HTTPException(
                status_code=400, 
                detail=f"File must be an image. Got: {kind.mime if kind else 'unknown'}"
            )
        
        logger.info(f"Analyzing image with Gemini Vision: {filename}")
        
        # Analyze with vision
        with open(perm_img_path, "rb") as f:
            raw = f.read()

        try:
            result = await asyncio.to_thread(analyze_image, raw)
        except RuntimeError as e:
            if "GEMINI_API_KEY" in str(e):
                logger.error("GEMINI_API_KEY missing from .env")
                raise HTTPException(status_code=500, detail="Vision service is not properly configured.")
            raise e
        
        if result.confidence == 0:
            logger.error(f"Vision failure: {result.description}")
            raise HTTPException(status_code=500, detail="Image analysis could not interpret the content.")
        
        # Create markdown document from vision result
        doc_title = title or filename
        markdown_text = f"""# {doc_title}

**Image Type:** {result.image_type}

## Analysis

{result.description}
"""
        logger.info(f"Vision analysis complete. Type: {result.image_type}, Content length: {len(result.description)}")
        
        # 2. Save Analysis MD (Persistent)
        perm_md_path = perm_img_path + ".md"
        with open(perm_md_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)

        # 3. Ingest
        doc_id = await engine.ingest_text_file(
            path=perm_md_path,
            title=doc_title,
            source=source,
            workspace_id=workspace_id,
            uri=perm_img_path # Persistent URI
        )
        return IngestResponse(status="ok", doc_id=doc_id)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = f"Image ingestion failed: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        with open("upload_error.log", "w") as f:
            f.write(error_msg)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during image processing.")


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
@limiter.limit("10/minute")
async def query(request: Request, req: QueryRequest) -> QueryResponse:
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
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process your query.")


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
