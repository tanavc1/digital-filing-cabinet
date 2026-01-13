"""
Vision Analyzer Module
======================

Multi-modal image analysis using Google Gemini Flash 2.0.
Provides:
1. Chart/graph analysis with data extraction
2. General image description for search indexing
3. Advanced OCR fallback for documents

Cost-effective: Gemini Flash is ~$0.10/1M input tokens
"""

import os
import io
import base64
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import google.generativeai as genai
from PIL import Image

logger = logging.getLogger(__name__)

# Configuration
GEMINI_MODEL = "gemini-2.0-flash"
MAX_IMAGE_SIZE = 1024  # Max dimension in pixels
MAX_IMAGES_PER_PDF = 10
MIN_IMAGE_SIZE_BYTES = 10 * 1024  # 10KB minimum
MIN_IMAGE_DIMENSION = 100  # 100px minimum width/height


@dataclass
class VisionResult:
    """Result of vision analysis."""
    description: str
    image_type: str  # "chart", "diagram", "photo", "document", "unknown"
    data_points: Optional[Dict[str, Any]] = None
    confidence: float = 0.0


# Lazy-loaded Gemini client
_gemini_model = None


def get_gemini_model():
    """Initialize Gemini model lazily."""
    global _gemini_model
    if _gemini_model is None:
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


def analyze_image(
    image_bytes: bytes,
    prompt: Optional[str] = None,
    image_type_hint: Optional[str] = None
) -> VisionResult:
    """
    Analyze an image using Gemini Vision.
    
    Args:
        image_bytes: Raw image bytes (PNG, JPG, etc.)
        prompt: Custom prompt override
        image_type_hint: Hint about image type ("chart", "document", etc.)
        
    Returns:
        VisionResult with description and metadata
    """
    try:
        model = get_gemini_model()
        
        # Resize if needed
        processed_bytes = resize_image(image_bytes)
        
        # Build prompt based on type
        if prompt:
            analysis_prompt = prompt
        elif image_type_hint == "chart":
            analysis_prompt = """Analyze this chart or graph image. Extract ALL information:

1. **Chart Type**: (bar, line, pie, scatter, etc.)
2. **Title**: The chart title if visible
3. **Axis Labels**: X-axis and Y-axis labels
4. **Data Points**: List ALL visible data points with their values
5. **Trends**: Describe any trends or patterns
6. **Key Insights**: Important observations

Format as structured Markdown with clear headings."""
        elif image_type_hint == "document":
            analysis_prompt = """This is a scanned document or photo of a document.
Extract ALL text content you can see.
Format the output to preserve the document structure.
Include any headers, paragraphs, tables, or lists."""
        else:
            analysis_prompt = """Analyze this image comprehensively:

1. **Description**: What does this image show?
2. **Text Content**: Any visible text (extract it fully)
3. **Data/Numbers**: Any numerical data, statistics, or measurements
4. **Context**: What type of content is this (chart, photo, diagram, document)?

Format as structured Markdown suitable for search indexing."""

        # Create image part for Gemini
        img = Image.open(io.BytesIO(processed_bytes))
        
        # Generate content
        response = model.generate_content([analysis_prompt, img])
        
        description = response.text.strip()
        
        # Infer image type from response
        image_type = "unknown"
        description_lower = description.lower()
        if any(word in description_lower for word in ["chart", "graph", "plot", "axis"]):
            image_type = "chart"
        elif any(word in description_lower for word in ["document", "page", "text", "form"]):
            image_type = "document"
        elif any(word in description_lower for word in ["diagram", "flowchart", "schema"]):
            image_type = "diagram"
        elif any(word in description_lower for word in ["photo", "picture", "image of"]):
            image_type = "photo"
        
        logger.info(f"Vision analysis complete. Type: {image_type}, Length: {len(description)} chars")
        
        return VisionResult(
            description=description,
            image_type=image_type,
            confidence=0.9  # Gemini doesn't provide confidence, assume high
        )
        
    except Exception as e:
        logger.error(f"Vision analysis failed: {e}")
        return VisionResult(
            description=f"[Image analysis failed: {str(e)}]",
            image_type="error",
            confidence=0.0
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
