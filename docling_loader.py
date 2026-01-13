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
        # Always default to OCR=True for complex PDFs as per user request
        self.enable_ocr = enable_ocr
        
        # Configure robust pipeline options
        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions, 
            TableStructureOptions,
            AcceleratorOptions
        )
        from docling.datamodel.settings import settings
        
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True  # Force OCR for better layout handling of complex docs
        pipeline_options.do_table_structure = True  # Critical for the USDA charts/tables
        pipeline_options.table_structure_options.do_cell_matching = True
        
        # Improve OCR quality
        pipeline_options.ocr_options.use_gpu = False # MPS not fully supported in Tesseract wrapper yet
        
        # Set accelerator to auto (cpu/cuda/mps if supported by docling internals)
        # pipeline_options.accelerator_options = AcceleratorOptions(num_threads=4)

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
