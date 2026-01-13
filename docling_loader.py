"""
Docling Integration (Non-PDF)
=============================

Refactored to handle primarily non-PDF formats (DOCX, PPTX, HTML, Images).
PDF processing has been moved to `pdf_extractor.py` for better stability on Python 3.13.

This module still uses Docling but with simplified options to avoid loading
broken layout models unless necessary.
"""
import os
from dataclasses import dataclass
from typing import Optional

from docling.document_converter import DocumentConverter


@dataclass(frozen=True)
class ExtractedDocument:
    text: str
    format: str
    title: str
    mime: Optional[str]
    used_ocr: bool


class DoclingExtractor:
    """
    Wrapper for Docling to handle non-PDF documents.
    """

    def __init__(self, enable_ocr: bool = True):
        self.enable_ocr = enable_ocr
        
        # Initialize default converter
        # logic for specific formats can be added here if needed
        self.converter = DocumentConverter()

    def extract(self, path: str, title: Optional[str] = None, mime: Optional[str] = None) -> ExtractedDocument:
        if not os.path.exists(path):
            raise FileNotFoundError(path)

        # Safety check: Redirect PDFs to explicit error or handling if this was called by mistake
        if path.lower().endswith('.pdf'):
            print(f"WARNING: DoclingExtractor called for PDF {path}. This should be handled by pdf_extractor.py")
            # We continue anyway as a fallback, but it might crash on Py3.13
        
        try:
            result = self.converter.convert(path)
            doc = result.document
            markdown = doc.export_to_markdown()
            
            return ExtractedDocument(
                text=markdown,
                format="markdown",
                title=title or os.path.basename(path),
                mime=mime,
                used_ocr=self.enable_ocr,
            )
        except Exception as e:
            raise RuntimeError(f"Docling conversion failed for {path}: {e}")
