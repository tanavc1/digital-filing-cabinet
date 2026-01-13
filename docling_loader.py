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

    def __init__(self, enable_ocr: bool = False):
        self.enable_ocr = enable_ocr
        if enable_ocr:
            pipeline_options = PipelineOptions()
            pipeline_options.do_ocr = True
            pipeline_options.ocr_options = TesseractOcrOptions()
            self.converter = DocumentConverter(pipeline_options=pipeline_options)
        else:
            self.converter = DocumentConverter()

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
