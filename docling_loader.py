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
        from docling.document_converter import PdfFormatOption
        from docling.datamodel.base_models import InputFormat
        # Configure robust pipeline options
        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions, 
            TableStructureOptions,
            EasyOcrOptions,
            RapidOcrOptions,
            AcceleratorOptions
        )

        # Always enable OCR if requested, using RapidOCR as the engine (pip installed)
        self.enable_ocr = enable_ocr
        
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = self.enable_ocr
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True
        
        # Limit Docling threads to prevent resource starvation
        pipeline_options.accelerator_options = AcceleratorOptions(num_threads=4, device="cpu")
        
        # Use RapidOCR (fast, accurate, pure python dependency)
        if self.enable_ocr:
            pipeline_options.ocr_options = RapidOcrOptions()

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
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
