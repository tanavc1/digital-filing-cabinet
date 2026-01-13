"""
Docling Integration
===================

Handles document parsing using the Docling library.
Capabilities:
- Universal Parsing (PDF, DOCX, PPTX, HTML, Images).
- Layout-aware extraction (preserves tables/headers).
- Optional OCR for scanned documents via Tesseract.
- Export to structured Markdown for robust chunking.
"""
import os
from dataclasses import dataclass
from typing import Optional

from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PipelineOptions, TesseractOcrOptions


@dataclass(frozen=True)
class ExtractedDocument:
    text: str
    format: str
    title: str
    mime: Optional[str]
    used_ocr: bool


class DoclingExtractor:
    """
    Production-shaped wrapper:
    - Converts many file types to DoclingDocument
    - Exports to Markdown for structure (tables/headings)
    - Optional OCR (Tesseract) for scanned PDFs/images
    """

    def __init__(self, enable_ocr: bool = True):
        # Check if tesseract is actually installed
        import shutil
        tesseract_available = shutil.which("tesseract") is not None
        
        # Only enable OCR if requested AND tesseract is available
        self.enable_ocr = enable_ocr and tesseract_available
        
        if enable_ocr and not tesseract_available:
            print("WARNING: OCR requested but 'tesseract' binary not found. Falling back to native PDF parsing.")
        
        # Configure robust pipeline options
        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions, 
            TableStructureOptions,
            AcceleratorOptions
        )
        from docling.datamodel.settings import settings
        
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = self.enable_ocr  # Only true if available
        pipeline_options.do_table_structure = True  # Keep table structure enabled
        pipeline_options.table_structure_options.do_cell_matching = True
        
        # Improve OCR quality settings (only relevant if OCR is on)
        if self.enable_ocr:
            pipeline_options.ocr_options.use_gpu = False 

        self.converter = DocumentConverter(
            format_options={
                "pdf": pipeline_options, # Apply specifically to PDF
            }
        )

    def extract(self, path: str, title: Optional[str] = None, mime: Optional[str] = None) -> ExtractedDocument:
        if not os.path.exists(path):
            raise FileNotFoundError(path)

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
