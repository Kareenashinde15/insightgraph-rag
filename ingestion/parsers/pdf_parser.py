from typing import List
from ingestion.parsers.base import BaseParser, ParsedDocument, ParsedChunkDraft

_OCR_ENGINE = None


def _ocr_page(page) -> str:
    """OCR a rendered PDF page when it contains no selectable text."""
    try:
        import fitz  # PyMuPDF
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise RuntimeError(
            "OCR dependencies are not installed; cannot read image-only PDFs."
        ) from exc

    # Keep OCR bounded while retaining enough resolution for normal scanned text.
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    image = np.frombuffer(pixmap.samples, dtype=np.uint8)
    image = image.reshape(pixmap.height, pixmap.width, pixmap.n)
    # PyMuPDF returns RGB pixels while OCR runtimes conventionally expect BGR.
    image = np.ascontiguousarray(image[:, :, :3][:, :, ::-1])
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        _OCR_ENGINE = RapidOCR()
    result, _ = _OCR_ENGINE(image)
    if not result:
        return ""
    return "\n".join(str(item[1]).strip() for item in result if len(item) > 1 and str(item[1]).strip())

class PDFParser(BaseParser):
    def parse(self, file_path: str, filename: str) -> ParsedDocument:
        drafts: List[ParsedChunkDraft] = []
        raw_text_parts: List[str] = []

        parse_errors: List[str] = []
        total_pages = 0
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            if reader.is_encrypted:
                # Handle PDFs protected with an empty owner/user password;
                # otherwise pypdf will raise a useful error below.
                reader.decrypt("")
            for page_idx, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text() or ""
                except Exception as page_error:
                    parse_errors.append(f"Page {page_idx + 1}: {page_error}")
                    page_text = ""

                # Scanned/image-only PDFs have no selectable text. Use OCR for
                # those pages so they remain searchable and citable.
                if not page_text.strip():
                    try:
                        import fitz
                        ocr_document = fitz.open(file_path)
                        page_text = _ocr_page(ocr_document[page_idx])
                        ocr_document.close()
                    except Exception as ocr_error:
                        parse_errors.append(f"Page {page_idx + 1} OCR: {ocr_error}")
                raw_text_parts.append(page_text)
                
                # Split page text into logical paragraphs
                paragraphs = [p.strip() for p in page_text.split("\n\n") if p.strip()]
                if not paragraphs and page_text.strip():
                    paragraphs = [page_text.strip()]

                for para_idx, para in enumerate(paragraphs):
                    first_line = para.splitlines()[0] if para.splitlines() else "General"
                    section = first_line[:60] if len(first_line) < 60 else "Content"
                    drafts.append(
                        ParsedChunkDraft(
                            page_number=page_idx + 1,
                            section=section,
                            paragraph=para,
                            text=para,
                            metadata={"page_index": page_idx, "para_index": para_idx},
                        )
                    )
        except Exception as e:
            parse_errors.append(f"PDF parsing failed: {type(e).__name__}: {e}")

        full_raw = "\n\n".join(raw_text_parts)
        return ParsedDocument(
            filename=filename,
            file_type="pdf",
            raw_text=full_raw,
            pages=drafts,
            metadata={
                "total_pages": total_pages,
                "extractable_text": bool(full_raw.strip()),
                "parse_errors": parse_errors,
            },
        )
