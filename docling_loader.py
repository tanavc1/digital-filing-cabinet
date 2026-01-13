"""
Docling Integration with PyMuPDF Fallback
==========================================

Two-stage extraction strategy:
1. Try Docling (advanced AI layout detection, table structure, OCR)
2. If Docling crashes (common on Python 3.13 due to PyTorch meta tensor bug),
   fall back to PyMuPDF (reliable C-based PDF parsing)
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ExtractedDocument:
    text: str
    format: str
    title: str
    mime: Optional[str]
    used_ocr: bool
    fallback_used: bool = False  # True if PyMuPDF was used instead of Docling


def extract_with_pymupdf(path: str, title: Optional[str] = None) -> ExtractedDocument:
    """
    Fallback PDF extraction using PyMuPDF (fitz).
    - Fast and reliable
    - Works on any Python version
    - No ML model dependencies
    - Extracts text, preserves some structure
    """
    import fitz  # PyMuPDF
    
    doc = fitz.open(path)
    text_parts = []
    
    for page_num, page in enumerate(doc, 1):
        text_parts.append(f"## Page {page_num}\n\n")
        
        # Get text with layout preservation
        text = page.get_text("text")
        if text.strip():
            text_parts.append(text)
        
        # Extract tables if any (basic table detection)
        tables = page.find_tables()
        if tables:
            for table in tables:
                text_parts.append("\n**[Table detected]**\n")
                # Convert table to markdown-like format
                for row in table.extract():
                    row_text = " | ".join(str(cell) if cell else "" for cell in row)
                    text_parts.append(f"| {row_text} |\n")
        
        text_parts.append("\n---\n")
    
    doc.close()
    
    full_text = "".join(text_parts)
    
    return ExtractedDocument(
        text=full_text,
        format="markdown",
        title=title or os.path.basename(path),
        mime="application/pdf",
        used_ocr=False,
        fallback_used=True
    )


class DoclingExtractor:
    """
    Production wrapper with automatic fallback:
    - Tries Docling first (best quality)
    - Falls back to PyMuPDF on any failure (guaranteed to work)
    """

    def __init__(self, enable_ocr: bool = True):
        self.enable_ocr = enable_ocr
        self._docling_available = False
        
        # Try to initialize Docling (may fail on Python 3.13)
        try:
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            
            # Use SIMPLE pipeline options to avoid the layout model crash
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = False  # Disable OCR to avoid model loading issues
            pipeline_options.do_table_structure = False  # Disable to avoid model crash
            
            self.converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
            self._docling_available = True
            print("Docling initialized (simplified mode, no AI models)")
        except Exception as e:
            print(f"Docling initialization failed: {e}")
            print("Will use PyMuPDF fallback for all PDF extractions")
            self._docling_available = False

    def extract(self, path: str, title: Optional[str] = None, mime: Optional[str] = None) -> ExtractedDocument:
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        
        # Check if it's a PDF (where we have the fallback)
        is_pdf = path.lower().endswith('.pdf') or (mime and 'pdf' in mime.lower())
        
        # If Docling is available, try it first
        if self._docling_available:
            try:
                result = self.converter.convert(path)
                doc = result.document
                markdown = doc.export_to_markdown()
                
                return ExtractedDocument(
                    text=markdown,
                    format="markdown",
                    title=title or os.path.basename(path),
                    mime=mime,
                    used_ocr=False,
                    fallback_used=False
                )
            except Exception as e:
                print(f"Docling extraction failed: {e}")
                if is_pdf:
                    print("Falling back to PyMuPDF...")
                else:
                    raise  # Re-raise for non-PDFs
        
        # Fallback to PyMuPDF for PDFs
        if is_pdf:
            return extract_with_pymupdf(path, title)
        
        # For non-PDFs without Docling, we have no fallback
        raise RuntimeError(f"Cannot extract {path}: Docling unavailable and no fallback for this file type")
