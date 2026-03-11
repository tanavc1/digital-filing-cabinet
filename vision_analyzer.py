"""
Vision Analyzer Module
======================

Multi-modal image analysis with provider abstraction.
Supports:
1. Google Gemini Flash (cloud) - default
2. Ollama Qwen3-VL (local) - air-gapped environments

Configured via VISION_PROVIDER env var: "gemini" or "ollama"
"""

import os
import io
import base64
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import httpx
from PIL import Image

logger = logging.getLogger(__name__)

# Configuration
MAX_IMAGE_SIZE = 1024  # Max dimension in pixels
MAX_IMAGES_PER_PDF = 10
MIN_IMAGE_SIZE_BYTES = 10 * 1024  # 10KB minimum
MIN_IMAGE_DIMENSION = 100  # 100px minimum width/height

# Provider configuration
VISION_PROVIDER = os.getenv("VISION_PROVIDER", "ollama")  # "ollama" (local, default) or "gemini"
GEMINI_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.0-flash")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "qwen3-vl:8b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


@dataclass
class VisionResult:
    """Result of vision analysis."""
    description: str
    image_type: str  # "chart", "diagram", "photo", "document", "unknown"
    data_points: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    provider: str = "unknown"


# Lazy-loaded clients
_gemini_model = None
_ollama_available = None


def _check_ollama_vision_available() -> bool:
    """Check if Ollama with vision model is available."""
    global _ollama_available
    if _ollama_available is None:
        try:
            import httpx
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{OLLAMA_HOST}/api/tags")
                if resp.status_code == 200:
                    models = [m["name"] for m in resp.json().get("models", [])]
                    _ollama_available = any("qwen3-vl" in m.lower() or "llava" in m.lower() for m in models)
                else:
                    _ollama_available = False
        except Exception:
            _ollama_available = False
    return _ollama_available


def get_gemini_model():
    """Initialize Gemini model lazily."""
    global _gemini_model
    if _gemini_model is None:
        import google.generativeai as genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set. Add it to your .env file.")
        
        genai.configure(api_key=api_key)
        _gemini_model = genai.GenerativeModel(GEMINI_MODEL)
        logger.info(f"Gemini model initialized: {GEMINI_MODEL}")
    
    return _gemini_model


def resize_image(image_bytes: bytes, max_size: int = MAX_IMAGE_SIZE) -> bytes:
    """Resize image to max dimension while preserving aspect ratio."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # Check if resize needed
        if max(img.size) <= max_size:
            return image_bytes
        
        # Calculate new size
        ratio = max_size / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        
        # Resize
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Save to bytes
        buffer = io.BytesIO()
        img_format = img.format or "PNG"
        img.save(buffer, format=img_format)
        buffer.seek(0)
        
        logger.debug(f"Resized image from {img.size} to {new_size}")
        return buffer.read()
        
    except Exception as e:
        logger.warning(f"Failed to resize image: {e}")
        return image_bytes


def _build_vision_prompt(image_type_hint: Optional[str] = None) -> str:
    """Build analysis prompt based on image type hint."""
    if image_type_hint == "chart":
        return """Analyze this chart or graph image. Extract ALL information:

1. **Chart Type**: (bar, line, pie, scatter, etc.)
2. **Title**: The chart title if visible
3. **Axis Labels**: X-axis and Y-axis labels
4. **Data Points**: List ALL visible data points with their values
5. **Trends**: Describe any trends or patterns
6. **Key Insights**: Important observations

Format as structured Markdown with clear headings."""
    elif image_type_hint == "document":
        return """This is a scanned document or photo of a document.
Extract ALL text content you can see.
Format the output to preserve the document structure.
Include any headers, paragraphs, tables, or lists."""
    else:
        return """Analyze this image comprehensively:

1. **Description**: What does this image show?
2. **Text Content**: Any visible text (extract it fully)
3. **Data/Numbers**: Any numerical data, statistics, or measurements
4. **Context**: What type of content is this (chart, photo, diagram, document)?

Format as structured Markdown suitable for search indexing."""


def _infer_image_type(description: str) -> str:
    """Infer image type from analysis description."""
    description_lower = description.lower()
    if any(word in description_lower for word in ["chart", "graph", "plot", "axis"]):
        return "chart"
    elif any(word in description_lower for word in ["document", "page", "text", "form"]):
        return "document"
    elif any(word in description_lower for word in ["diagram", "flowchart", "schema"]):
        return "diagram"
    elif any(word in description_lower for word in ["photo", "picture", "image of"]):
        return "photo"
    return "unknown"


def _analyze_image_ollama(
    image_bytes: bytes,
    prompt: str
) -> VisionResult:
    """
    Analyze image using Ollama with Qwen3-VL model (local).
    """
    try:
        # Resize for efficiency
        processed_bytes = resize_image(image_bytes)
        
        # Encode as base64
        b64_image = base64.b64encode(processed_bytes).decode("utf-8")
        
        # Call Ollama
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": OLLAMA_VISION_MODEL,
                    "prompt": prompt,
                    "images": [b64_image],
                    "stream": False
                }
            )
            resp.raise_for_status()
            description = resp.json()["response"].strip()
        
        image_type = _infer_image_type(description)
        logger.info(f"Ollama vision analysis complete. Type: {image_type}, Length: {len(description)} chars")
        
        return VisionResult(
            description=description,
            image_type=image_type,
            confidence=0.85,
            provider="ollama"
        )
        
    except Exception as e:
        logger.error(f"Ollama vision analysis failed: {e}")
        return VisionResult(
            description=f"[Local vision analysis failed: {str(e)}]",
            image_type="error",
            confidence=0.0,
            provider="ollama"
        )


def _analyze_image_gemini(
    image_bytes: bytes,
    prompt: str
) -> VisionResult:
    """
    Analyze image using Google Gemini (cloud).
    """
    try:
        model = get_gemini_model()
        
        # Resize if needed
        processed_bytes = resize_image(image_bytes)
        
        # Create image for Gemini
        img = Image.open(io.BytesIO(processed_bytes))
        
        # Generate content
        response = model.generate_content([prompt, img])
        description = response.text.strip()
        
        image_type = _infer_image_type(description)
        logger.info(f"Gemini vision analysis complete. Type: {image_type}, Length: {len(description)} chars")
        
        return VisionResult(
            description=description,
            image_type=image_type,
            confidence=0.9,
            provider="gemini"
        )
        
    except Exception as e:
        logger.error(f"Gemini vision analysis failed: {e}")
        return VisionResult(
            description=f"[Cloud vision analysis failed: {str(e)}]",
            image_type="error",
            confidence=0.0,
            provider="gemini"
        )


def analyze_image(
    image_bytes: bytes,
    prompt: Optional[str] = None,
    image_type_hint: Optional[str] = None
) -> VisionResult:
    """
    Analyze an image using the configured vision provider.
    
    Provider is determined by VISION_PROVIDER env var:
    - "ollama" (default): Qwen3-VL via Ollama (local, private)
    - "gemini": Google Gemini Flash (cloud, requires API key)
    
    Args:
        image_bytes: Raw image bytes (PNG, JPG, etc.)
        prompt: Custom prompt override
        image_type_hint: Hint about image type ("chart", "document", etc.)
        
    Returns:
        VisionResult with description and metadata
    """
    # Build the analysis prompt
    analysis_prompt = prompt or _build_vision_prompt(image_type_hint)
    
    # Route to appropriate provider
    provider = VISION_PROVIDER.lower().strip()
    
    if provider == "gemini":
        # Explicit cloud request
        return _analyze_image_gemini(image_bytes, analysis_prompt)
    
    # Default: local Ollama
    if _check_ollama_vision_available():
        return _analyze_image_ollama(image_bytes, analysis_prompt)
    
    # Fallback: try Gemini if API key is available
    if os.getenv("GEMINI_API_KEY"):
        logger.warning("Ollama vision not available, falling back to Gemini")
        return _analyze_image_gemini(image_bytes, analysis_prompt)
    
    # No vision provider available
    logger.warning("No vision provider available (Ollama not running, no GEMINI_API_KEY)")
    return VisionResult(
        description="[Vision analysis unavailable: Install Ollama and run 'ollama pull qwen3-vl:8b' for local image analysis]",
        image_type="error",
        confidence=0.0,
        provider="none"
    )


def analyze_chart(image_bytes: bytes) -> VisionResult:
    """Specialized analysis for charts and graphs."""
    return analyze_image(image_bytes, image_type_hint="chart")


def analyze_document_image(image_bytes: bytes) -> VisionResult:
    """Specialized analysis for document scans/photos."""
    return analyze_image(image_bytes, image_type_hint="document")


def should_analyze_image(image_bytes: bytes, width: int, height: int) -> bool:
    """Determine if an image is worth analyzing (not too small or trivial)."""
    # Size checks
    if len(image_bytes) < MIN_IMAGE_SIZE_BYTES:
        return False
    if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
        return False
    
    # Aspect ratio check (skip very thin/tall images like decorative bars)
    aspect = max(width, height) / max(min(width, height), 1)
    if aspect > 10:  # Very thin image
        return False
    
    return True


def format_vision_result_as_markdown(result: VisionResult, image_index: int = 1) -> str:
    """Format a vision result as Markdown for embedding in documents."""
    type_label = result.image_type.title() if result.image_type != "unknown" else "Image"
    
    return f"""

---
**[{type_label} {image_index}]**

{result.description}

---
"""
