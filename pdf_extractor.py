"""
Enhanced PDF Extractor with OCR
===============================

Hybrid extraction strategy:
1. Native text extraction using PyMuPDF (fast, preserves formatting)
2. OCR for scanned/image-based pages using RapidOCR
3. Table detection and formatting
4. Intelligent page analysis to determine extraction method

Features:
- Automatically detects scanned vs text-based pages
- Renders image-heavy pages for OCR at optimal DPI
- Extracts and formats tables as Markdown
- Preserves reading order and structure
"""

import os
import io
import logging
from dataclasses import dataclass
from typing import Optional, List, Tuple
import numpy as np

# PyMuPDF for PDF parsing
import fitz

# RapidOCR for image-to-text
from rapidocr_onnxruntime import RapidOCR

logger = logging.getLogger(__name__)


@dataclass
class PageContent:
    """Content extracted from a single PDF page."""
    page_num: int
    text: str
    tables: List[str]
    used_ocr: bool
    

@dataclass
class PDFExtractionResult:
    """Complete extraction result from a PDF."""
    text: str
    page_count: int
    pages_with_ocr: int
    tables_found: int
    title: str


# Global OCR instance (lazy loaded)
_ocr_engine: Optional[RapidOCR] = None


def get_ocr_engine() -> RapidOCR:
    """Lazy-load the OCR engine to avoid startup cost if not needed."""
    global _ocr_engine
    if _ocr_engine is None:
        logger.info("Initializing RapidOCR engine...")
        _ocr_engine = RapidOCR()
        logger.info("RapidOCR engine ready.")
    return _ocr_engine


def is_scanned_page(page: fitz.Page, text: str, min_chars_per_page: int = 50) -> bool:
    """
    Determine if a page needs OCR based on content analysis.
    
    A page is considered "scanned" (needing OCR) if:
    - It has very little extractable text (< min_chars_per_page)
    - AND it has images that cover significant area
    
    Args:
        page: PyMuPDF page object
        text: Already extracted text from the page
        min_chars_per_page: Threshold for "meaningful" text content
        
    Returns:
        True if OCR should be applied
    """
    # If we have decent text, no need for OCR
    text_clean = text.strip()
    if len(text_clean) >= min_chars_per_page:
        return False
    
    # Check if page has images
    image_list = page.get_images(full=True)
    if not image_list:
        return False  # No images and no text - just an empty page
    
    # Calculate image coverage
    page_area = page.rect.width * page.rect.height
    total_image_area = 0
    
    for img in image_list:
        try:
            xref = img[0]
            bbox = page.get_image_bbox(img)
            if bbox:
                total_image_area += bbox.width * bbox.height
        except Exception:
            pass
    
    # If images cover more than 30% of page, likely needs OCR
    image_coverage = total_image_area / page_area if page_area > 0 else 0
    
    return image_coverage > 0.3 or (len(text_clean) < 10 and len(image_list) > 0)


def ocr_page(page: fitz.Page, dpi: int = 200) -> str:
    """
    Render page to image and run OCR.
    
    Args:
        page: PyMuPDF page object
        dpi: Resolution for rendering (higher = better quality but slower)
        
    Returns:
        Extracted text from OCR
    """
    try:
        ocr = get_ocr_engine()
        
        # Render page to pixmap
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # Convert to numpy array for RapidOCR
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        
        # Run OCR
        result, _ = ocr(img_array)
        
        if result is None:
            return ""
        
        # RapidOCR returns list of (bbox, text, confidence)
        # Sort by y-coordinate (top to bottom) then x (left to right)
        lines = []
        if result:
            # Group by approximate y-position (line grouping)
            sorted_results = sorted(result, key=lambda x: (x[0][0][1], x[0][0][0]))
            for item in sorted_results:
                text = item[1]
                if text.strip():
                    lines.append(text.strip())
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"OCR failed for page: {e}")
        return ""


def extract_tables(page: fitz.Page) -> List[str]:
    """
    Extract tables from page and format as Markdown.
    
    Args:
        page: PyMuPDF page object
        
    Returns:
        List of tables formatted as Markdown strings
    """
    tables = []
    
    try:
        found_tables = page.find_tables()
        
        for table in found_tables:
            rows = table.extract()
            if not rows:
                continue
            
            # Build Markdown table
            md_lines = []
            
            # Header row
            header = rows[0]
            header_str = "| " + " | ".join(str(cell) if cell else "" for cell in header) + " |"
            md_lines.append(header_str)
            
            # Separator
            separator = "| " + " | ".join("---" for _ in header) + " |"
            md_lines.append(separator)
            
            # Data rows
            for row in rows[1:]:
                row_str = "| " + " | ".join(str(cell) if cell else "" for cell in row) + " |"
                md_lines.append(row_str)
            
            tables.append("\n".join(md_lines))
            
    except Exception as e:
        logger.debug(f"Table extraction failed: {e}")
    
    return tables


def extract_page(page: fitz.Page, page_num: int, enable_ocr: bool = True) -> PageContent:
    """
    Extract content from a single page using the best available method.
    
    Args:
        page: PyMuPDF page object
        page_num: 1-indexed page number
        enable_ocr: Whether to use OCR for scanned pages
        
    Returns:
        PageContent with text, tables, and metadata
    """
    # First, try native text extraction
    native_text = page.get_text("text")
    
    # Extract tables
    tables = extract_tables(page)
    
    # Determine if we need OCR
    used_ocr = False
    final_text = native_text
    
    if enable_ocr and is_scanned_page(page, native_text):
        logger.info(f"Page {page_num}: Detected as scanned, running OCR...")
        ocr_text = ocr_page(page)
        
        if ocr_text:
            # OCR produced better results
            final_text = ocr_text
            used_ocr = True
            logger.info(f"Page {page_num}: OCR extracted {len(ocr_text)} chars")
    
    return PageContent(
        page_num=page_num,
        text=final_text,
        tables=tables,
        used_ocr=used_ocr
    )


def extract_pdf(
    path: str, 
    title: Optional[str] = None,
    enable_ocr: bool = True
) -> PDFExtractionResult:
    """
    Extract all content from a PDF file.
    
    This is the main entry point for PDF extraction. It:
    1. Opens the PDF with PyMuPDF
    2. Extracts text from each page (native or OCR)
    3. Extracts tables and formats as Markdown
    4. Combines everything into a structured Markdown document
    
    Args:
        path: Path to PDF file
        title: Optional title override (otherwise uses filename)
        enable_ocr: Whether to enable OCR for scanned pages
        
    Returns:
        PDFExtractionResult with complete extracted content
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"PDF not found: {path}")
    
    doc = fitz.open(path)
    pdf_title = title or os.path.basename(path)
    
    all_parts = []
    pages_with_ocr = 0
    total_tables = 0
    
    logger.info(f"Extracting PDF: {pdf_title} ({doc.page_count} pages, OCR={enable_ocr})")
    
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        content = extract_page(page, page_num + 1, enable_ocr)
        
        # Build page section
        page_parts = [f"## Page {content.page_num}"]
        
        if content.text.strip():
            page_parts.append(content.text.strip())
        
        if content.tables:
            for i, table in enumerate(content.tables, 1):
                page_parts.append(f"\n**Table {i}:**\n{table}")
            total_tables += len(content.tables)
        
        if content.used_ocr:
            pages_with_ocr += 1
        
        all_parts.append("\n\n".join(page_parts))
    
    # Add metadata header
    header = f"# {pdf_title}\n\n"
    if pages_with_ocr > 0:
        header += f"*OCR was used on {pages_with_ocr} of {doc.page_count} pages*\n\n"
    
    result = PDFExtractionResult(
        text=header + full_text,
        page_count=doc.page_count,
        pages_with_ocr=pages_with_ocr,
        tables_found=total_tables,
        title=pdf_title
    )
    
    doc.close()

    logger.info(f"Extraction complete: {len(result.text)} chars, {pages_with_ocr} OCR pages, {total_tables} tables")
    
    return result


# Convenience function for quick extraction
def quick_extract(path: str, enable_ocr: bool = True) -> str:
    """
    Quick extraction that just returns the text.
    
    Args:
        path: Path to PDF file
        enable_ocr: Whether to enable OCR
        
    Returns:
        Extracted text as string
    """
    result = extract_pdf(path, enable_ocr=enable_ocr)
    return result.text
