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
import zipfile
import shutil
import uuid
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


class ZipIngestResponse(BaseModel):
    """Response for bulk ZIP ingestion."""
    status: str
    total_files: int
    ingested: int
    skipped: int
    errors: List[str] = []
    doc_ids: List[str] = []


class QueryRequest(BaseModel):
    q: str
    workspace_id: Optional[str] = "default"
    doc_id: Optional[str] = None
    doc_ids: Optional[List[str]] = None
    folder_path: Optional[str] = None  # Filter by folder (e.g., "Legal/Contracts")
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
    folder_path: Optional[str] = None,
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
    - folder_path: Original folder path within a Data Room (for filtering).
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
            uri=perm_bin_path, # Point to the original file
            folder_path=folder_path
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


# Supported file extensions for ZIP ingestion
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.pptx', '.xlsx', '.txt', '.md', '.html', '.htm', '.png', '.jpg', '.jpeg', '.gif', '.webp'}


@app.post("/ingest/zip", response_model=ZipIngestResponse)
async def ingest_zip(
    workspace_id: str = DEFAULT_WORKSPACE_ID,
    source: str = "dataroom",
    enable_ocr: bool = False,
    enable_vision: bool = False,
    file: UploadFile = File(...),
) -> ZipIngestResponse:
    """
    Bulk Data Room ingestion from a ZIP file.
    
    - Extracts the ZIP archive.
    - Recursively walks all folders.
    - Ingests each supported file (PDF, DOCX, TXT, images, etc.).
    - Preserves folder paths as metadata for filtering.
    
    Returns summary of ingested files.
    """
    engine = get_engine()
    
    # Validate it's a ZIP
    if not file.filename or not file.filename.lower().endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive.")
    
    # Save ZIP to temp
    temp_zip_dir = tempfile.mkdtemp(prefix="zip_upload_")
    zip_path = os.path.join(temp_zip_dir, file.filename)
    
    try:
        # Save uploaded file
        with open(zip_path, "wb") as f:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                f.write(content)
        
        # Extract ZIP
        extract_dir = os.path.join(temp_zip_dir, "extracted")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        logger.info(f"Extracted ZIP to {extract_dir}")
        
        # Walk extracted files
        total_files = 0
        ingested = 0
        skipped = 0
        errors = []
        doc_ids = []
        
        for root, dirs, files in os.walk(extract_dir):
            # Skip hidden directories (like __MACOSX)
            dirs[:] = [d for d in dirs if not d.startswith('.') and not d.startswith('__')]
            
            for filename in files:
                # Skip hidden files
                if filename.startswith('.'):
                    continue
                    
                _, ext = os.path.splitext(filename)
                if ext.lower() not in SUPPORTED_EXTENSIONS:
                    skipped += 1
                    continue
                
                total_files += 1
                file_path = os.path.join(root, filename)
                
                # Calculate relative folder path (e.g., "Legal/Contracts")
                rel_path = os.path.relpath(file_path, extract_dir)
                folder_path = os.path.dirname(rel_path)
                if folder_path == '.':
                    folder_path = ''
                
                logger.info(f"Ingesting: {rel_path} (folder: {folder_path})")
                
                try:
                    # Determine if image or document
                    is_image = ext.lower() in {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
                    
                    if is_image:
                        # Use vision analyzer
                        from vision_analyzer import analyze_image
                        
                        with open(file_path, "rb") as img_f:
                            raw = img_f.read()
                        
                        result = await asyncio.to_thread(analyze_image, raw)
                        
                        # Create markdown from vision
                        markdown_text = f"# {filename}\n\n**Image Type:** {result.image_type}\n\n## Analysis\n\n{result.description}"
                        
                        # Save markdown
                        perm_dir = os.path.join(os.getenv("UPLOAD_DIR", "./data/uploads"), workspace_id)
                        os.makedirs(perm_dir, exist_ok=True)
                        
                        file_id = str(uuid.uuid4())
                        perm_img_path = os.path.join(perm_dir, f"{file_id}_{filename}")
                        shutil.copy(file_path, perm_img_path)
                        
                        perm_md_path = perm_img_path + ".md"
                        with open(perm_md_path, "w", encoding="utf-8") as md_f:
                            md_f.write(markdown_text)
                        
                        doc_id = await engine.ingest_text_file(
                            path=perm_md_path,
                            title=filename,
                            source=source,
                            workspace_id=workspace_id,
                            uri=perm_img_path,
                            folder_path=folder_path
                        )
                    else:
                        # Copy to persistent storage
                        perm_dir = os.path.join(os.getenv("UPLOAD_DIR", "./data/uploads"), workspace_id)
                        os.makedirs(perm_dir, exist_ok=True)
                        
                        file_id = str(uuid.uuid4())
                        perm_path = os.path.join(perm_dir, f"{file_id}_{filename}")
                        shutil.copy(file_path, perm_path)
                        
                        # Extract text based on file type
                        if ext.lower() == '.txt' or ext.lower() == '.md':
                            with open(perm_path, "r", encoding="utf-8") as txt_f:
                                extracted_text = txt_f.read()
                        elif ext.lower() == '.pdf':
                            import pdf_extractor
                            result = await asyncio.to_thread(
                                pdf_extractor.extract_pdf,
                                perm_path,
                                title=filename,
                                enable_ocr=enable_ocr,
                                enable_vision=enable_vision
                            )
                            extracted_text = result.text
                        else:
                            # Use Docling for other formats
                            extractor = get_docling_extractor(enable_ocr=enable_ocr)
                            kind = filetype.guess(perm_path)
                            guessed_mime = kind.mime if kind else None
                            
                            extracted = await asyncio.to_thread(
                                extractor.extract,
                                perm_path,
                                title=filename,
                                mime=guessed_mime
                            )
                            extracted_text = extracted.text
                        
                        # Save extracted markdown
                        perm_md_path = perm_path + ".md"
                        with open(perm_md_path, "w", encoding="utf-8") as md_f:
                            md_f.write(extracted_text)
                        
                        # Ingest
                        doc_id = await engine.ingest_text_file(
                            path=perm_md_path,
                            title=filename,
                            source=source,
                            workspace_id=workspace_id,
                            uri=perm_path,
                            folder_path=folder_path
                        )
                    
                    doc_ids.append(doc_id)
                    ingested += 1
                    
                except Exception as e:
                    error_msg = f"{rel_path}: {str(e)}"
                    logger.error(f"Failed to ingest {rel_path}: {e}")
                    errors.append(error_msg)
        
        return ZipIngestResponse(
            status="ok",
            total_files=total_files,
            ingested=ingested,
            skipped=skipped,
            errors=errors[:10],  # Limit errors in response
            doc_ids=doc_ids
        )
        
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid or corrupted ZIP file.")
    except Exception as e:
        logger.error(f"ZIP ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_zip_dir, ignore_errors=True)


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
            async for event in engine.query_stream(body.q, body.workspace_id, body.messages, folder_path=body.folder_path):
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


# ----------------------------
# Audit Endpoints
# ----------------------------
from audit_templates import list_templates, get_template, get_questions


class AuditRequest(BaseModel):
    """Request to run an audit."""
    workspace_id: str = "default"
    folder_path: Optional[str] = None
    template_id: Optional[str] = None  # Use predefined template
    custom_questions: Optional[List[str]] = None  # Or provide custom questions


class AuditCitation(BaseModel):
    doc_id: str
    quote: str
    chunk_id: Optional[str] = None


class AuditFinding(BaseModel):
    question: str
    answer: str
    status: str  # FOUND, NOT_FOUND, UNCLEAR, ERROR
    severity: str  # HIGH, MEDIUM, LOW, INFO
    category: str
    citations: List[AuditCitation] = []


class AuditResponse(BaseModel):
    audit_id: str
    template_name: Optional[str] = None
    folder_path: Optional[str] = None
    findings: List[AuditFinding]
    summary: Dict[str, int]  # found, not_found, unclear, high_risk


@app.get("/audit/templates")
async def list_audit_templates():
    """List all available audit templates."""
    return {"templates": list_templates()}


@app.get("/audit/templates/{template_id}")
async def get_audit_template(template_id: str):
    """Get details of a specific audit template."""
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return template


@app.post("/audit/run", response_model=AuditResponse)
async def run_audit(body: AuditRequest):
    """
    Run an automated audit against a workspace/folder.
    
    Either provide a template_id to use predefined questions,
    or provide custom_questions for ad-hoc audits.
    """
    import uuid
    
    engine = get_engine()
    audit_id = str(uuid.uuid4())[:8]
    template_name = None
    
    # Get questions from template or custom
    if body.template_id:
        template = get_template(body.template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{body.template_id}' not found")
        questions = template["questions"]
        template_name = template["name"]
    elif body.custom_questions:
        questions = [
            {"text": q, "severity": "MEDIUM", "category": "Custom"}
            for q in body.custom_questions
        ]
    else:
        raise HTTPException(
            status_code=400, 
            detail="Must provide either template_id or custom_questions"
        )
    
    logger.info(f"Running audit '{audit_id}' with {len(questions)} questions on folder '{body.folder_path}'")
    
    # Pre-check: Verify documents exist in the target scope
    try:
        all_docs = engine.list_documents(workspace_id=body.workspace_id)
        if body.folder_path:
            scoped_docs = [d for d in all_docs if d.get("folder_path", "").startswith(body.folder_path)]
        else:
            scoped_docs = all_docs
        
        if not scoped_docs:
            return AuditResponse(
                audit_id=audit_id,
                template_name=template_name,
                folder_path=body.folder_path,
                findings=[],
                summary={"found": 0, "not_found": 0, "unclear": 0, "errors": 0, "high_risk": 0}
            )
    except Exception as e:
        logger.warning(f"Could not pre-check documents: {e}")
    
    try:
        findings = await engine.run_audit(
            questions=questions,
            workspace_id=body.workspace_id,
            folder_path=body.folder_path
        )
        
        # Calculate summary
        summary = {
            "found": sum(1 for f in findings if f["status"] == "FOUND"),
            "not_found": sum(1 for f in findings if f["status"] == "NOT_FOUND"),
            "unclear": sum(1 for f in findings if f["status"] == "UNCLEAR"),
            "errors": sum(1 for f in findings if f["status"] == "ERROR"),
            "high_risk": sum(1 for f in findings if f["status"] == "FOUND" and f["severity"] == "HIGH"),
        }
        
        return AuditResponse(
            audit_id=audit_id,
            template_name=template_name,
            folder_path=body.folder_path,
            findings=[AuditFinding(**f) for f in findings],
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------
# Document Comparison Endpoints
# ----------------------------

class CompareRequest(BaseModel):
    """Request to compare two documents."""
    doc_id_a: str  # Original document
    doc_id_b: str  # Revised document
    workspace_id: str = "default"


class DifferenceItem(BaseModel):
    """A single difference found between documents."""
    category: str
    description: str
    severity: str  # HIGH, MEDIUM, LOW
    original_text: Optional[str] = None
    revised_text: Optional[str] = None


class DocumentInfo(BaseModel):
    """Document metadata for comparison result."""
    doc_id: str
    title: str
    chunk_count: int


class CompareStats(BaseModel):
    """Statistics about the comparison."""
    total_changes: int
    high_severity: int
    medium_severity: int
    low_severity: int


class CompareResponse(BaseModel):
    """Response from document comparison."""
    doc_a: DocumentInfo
    doc_b: DocumentInfo
    differences: List[DifferenceItem]
    summary: str
    stats: CompareStats
    error: Optional[str] = None


@app.post("/compare", response_model=CompareResponse)
async def compare_documents(body: CompareRequest):
    """
    Compare two documents and identify material differences.
    
    Uses semantic analysis to find substantive changes, ignoring
    formatting and minor wording differences.
    """
    engine = get_engine()
    
    logger.info(f"Comparing documents: {body.doc_id_a} vs {body.doc_id_b}")
    
    try:
        result = await engine.compare_documents(
            doc_id_a=body.doc_id_a,
            doc_id_b=body.doc_id_b,
            workspace_id=body.workspace_id
        )
        
        return CompareResponse(
            doc_a=DocumentInfo(**result["doc_a"]),
            doc_b=DocumentInfo(**result["doc_b"]),
            differences=[DifferenceItem(**d) for d in result.get("differences", [])],
            summary=result.get("summary", ""),
            stats=CompareStats(**result.get("stats", {"total_changes": 0, "high_severity": 0, "medium_severity": 0, "low_severity": 0})),
            error=result.get("error")
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Run with:
# uvicorn api:app --host 0.0.0.0 --port 8000
