"""OpenDataLoader-backed PDF parsing with a bounded OCR fallback.

OpenDataLoader is the primary parser because its JSON output preserves page
numbers, headings, semantic element types, and bounding boxes. Those
annotations flow into the normal page-aware chunker and make citations more
useful without introducing vector embeddings.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List

from ingestion.parsers.base import BaseParser, ParsedChunkDraft, ParsedDocument

_OCR_ENGINE = None


def _content_to_text(value: Any) -> str:
    """Convert OpenDataLoader element content into searchable plain text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "\n".join(part for part in (_content_to_text(item) for item in value) if part)
    if isinstance(value, dict):
        for key in ("text", "content", "value", "alt", "cells", "items"):
            if key in value:
                text = _content_to_text(value[key])
                if text:
                    return text
        return "\n".join(
            f"{key}: {text}"
            for key, raw in value.items()
            if (text := _content_to_text(raw)) and key not in {"bounding box", "bbox"}
        )
    return str(value).strip()


def _iter_elements(value: Any) -> Iterable[Dict[str, Any]]:
    """Walk OpenDataLoader's nested JSON element tree."""
    if isinstance(value, dict):
        if "type" in value and any(key in value for key in ("content", "text", "alt", "kids")):
            yield value
        for child_key in ("kids", "children", "elements"):
            child = value.get(child_key)
            if isinstance(child, (dict, list)):
                yield from _iter_elements(child)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_elements(item)


def _element_text(element: Dict[str, Any]) -> str:
    for key in ("content", "text", "alt"):
        text = _content_to_text(element.get(key))
        if text:
            return text
    return ""


def _opendataloader_parse(file_path: str, filename: str) -> ParsedDocument:
    try:
        import opendataloader_pdf
    except ImportError as exc:
        raise RuntimeError(
            "OpenDataLoader is not installed; install opendataloader-pdf and Java 11+ is required."
        ) from exc

    with tempfile.TemporaryDirectory(prefix="opendataloader-") as output_dir:
        options: Dict[str, Any] = {
            "output_dir": output_dir,
            "format": "json,markdown",
            "quiet": True,
            "keep_line_breaks": True,
            "include_header_footer": False,
        }
        hybrid = os.getenv("OPENDATALOADER_HYBRID", "").strip()
        if hybrid:
            options["hybrid"] = hybrid
        hybrid_url = os.getenv("OPENDATALOADER_HYBRID_URL", "").strip()
        if hybrid_url:
            options["hybrid_url"] = hybrid_url
        hybrid_mode = os.getenv("OPENDATALOADER_HYBRID_MODE", "").strip()
        if hybrid_mode:
            options["hybrid_mode"] = hybrid_mode

        opendataloader_pdf.convert(file_path, **options)
        json_files = [path for path in Path(output_dir).rglob("*.json") if path.is_file()]
        if not json_files:
            raise RuntimeError("OpenDataLoader did not produce JSON output.")

        with json_files[0].open("r", encoding="utf-8") as stream:
            payload = json.load(stream)

        total_pages = int(payload.get("number of pages", 0) or 0) if isinstance(payload, dict) else 0
        drafts: List[ParsedChunkDraft] = []
        raw_text_parts: List[str] = []
        current_section = "Document"
        element_count = 0

        for element in _iter_elements(payload):
            text = _element_text(element)
            if not text:
                continue
            element_count += 1
            page_number = int(element.get("page number", 1) or 1)
            element_type = str(element.get("type", "paragraph")).lower()
            if element_type in {"title", "heading"}:
                current_section = text.splitlines()[0][:160]
            section = current_section or f"Page {page_number}"
            metadata = {
                "parser": "opendataloader",
                "element_type": element_type,
                "element_id": element.get("id"),
                "bounding_box": element.get("bounding box") or element.get("bbox"),
                "heading_level": element.get("heading level"),
                "pdfua_tag": element.get("pdfua_tag"),
            }
            drafts.append(
                ParsedChunkDraft(
                    page_number=page_number,
                    section=section,
                    paragraph=text[:240],
                    text=text,
                    metadata={key: value for key, value in metadata.items() if value is not None},
                )
            )
            raw_text_parts.append(text)

        if not drafts:
            markdown_files = [path for path in Path(output_dir).rglob("*.md") if path.is_file()]
            if markdown_files:
                markdown = markdown_files[0].read_text(encoding="utf-8", errors="replace").strip()
                if markdown and not markdown.startswith("![]("):
                    drafts.append(
                        ParsedChunkDraft(
                            page_number=None,
                            section="Document",
                            paragraph=markdown[:240],
                            text=markdown,
                            metadata={"parser": "opendataloader-markdown"},
                        )
                    )
                    raw_text_parts.append(markdown)

        return ParsedDocument(
            filename=filename,
            file_type="pdf",
            raw_text="\n\n".join(raw_text_parts),
            pages=drafts,
            metadata={
                "parser": "opendataloader",
                "total_pages": total_pages,
                "structured_elements": element_count,
                "extractable_text": bool(raw_text_parts),
                "parse_errors": [],
            },
        )


def _ocr_page(page) -> str:
    """OCR a rendered PDF page when it contains no selectable text."""
    try:
        import fitz  # PyMuPDF
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise RuntimeError("OCR dependencies are not installed for image-only PDFs.") from exc

    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    image = np.frombuffer(pixmap.samples, dtype=np.uint8)
    image = image.reshape(pixmap.height, pixmap.width, pixmap.n)
    image = np.ascontiguousarray(image[:, :, :3][:, :, ::-1])
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        _OCR_ENGINE = RapidOCR()
    result, _ = _OCR_ENGINE(image)
    if not result:
        return ""
    return "\n".join(str(item[1]).strip() for item in result if len(item) > 1 and str(item[1]).strip())


def _ocr_fallback(file_path: str, filename: str, prior_errors: List[str]) -> ParsedDocument:
    drafts: List[ParsedChunkDraft] = []
    raw_text_parts: List[str] = []
    errors = list(prior_errors)
    total_pages = 0
    try:
        import fitz

        pdf = fitz.open(file_path)
        total_pages = len(pdf)
        for page_idx, page in enumerate(pdf):
            page_text = (page.get_text("text") or "").strip()
            if not page_text:
                try:
                    page_text = _ocr_page(page).strip()
                except Exception as ocr_error:
                    errors.append(f"Page {page_idx + 1} OCR: {ocr_error}")
            if not page_text:
                continue
            raw_text_parts.append(page_text)
            paragraphs = [part.strip() for part in page_text.split("\n\n") if part.strip()] or [page_text]
            for para_idx, paragraph in enumerate(paragraphs):
                first_line = paragraph.splitlines()[0] if paragraph.splitlines() else "General"
                drafts.append(
                    ParsedChunkDraft(
                        page_number=page_idx + 1,
                        section=first_line[:160],
                        paragraph=paragraph[:240],
                        text=paragraph,
                        metadata={
                            "parser": "opendataloader-ocr-fallback",
                            "page_index": page_idx,
                            "para_index": para_idx,
                        },
                    )
                )
        pdf.close()
    except Exception as exc:
        errors.append(f"OCR fallback failed: {type(exc).__name__}: {exc}")

    return ParsedDocument(
        filename=filename,
        file_type="pdf",
        raw_text="\n\n".join(raw_text_parts),
        pages=drafts,
        metadata={
            "parser": "opendataloader-ocr-fallback",
            "total_pages": total_pages,
            "structured_elements": 0,
            "extractable_text": bool(raw_text_parts),
            "parse_errors": errors,
        },
    )


class PDFParser(BaseParser):
    def parse(self, file_path: str, filename: str) -> ParsedDocument:
        try:
            parsed = _opendataloader_parse(file_path, filename)
            if parsed.raw_text.strip():
                return parsed
            return _ocr_fallback(
                file_path,
                filename,
                ["OpenDataLoader found no textual elements; used OCR fallback."],
            )
        except Exception as exc:
            return _ocr_fallback(
                file_path,
                filename,
                [f"OpenDataLoader failed: {type(exc).__name__}: {exc}"],
            )
