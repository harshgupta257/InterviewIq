"""Text extraction from uploaded resumes (PDF, DOCX). Nothing is persisted or logged.

Defences: extension + MIME + magic-byte checks, size limits, page limits, zip-bomb
limits for DOCX, and a cap on extracted text. Scanned (image-only) PDFs are detected
and reported rather than silently returning nothing.
"""

import io
import re
import zipfile
from dataclasses import dataclass, field
from xml.etree import ElementTree

from app.core.exceptions import AppError

MAX_PAGES = 25
MAX_TEXT_CHARS = 15000  # matches the session resume limit
MAX_DOCX_XML_BYTES = 8 * 1024 * 1024
MAX_DOCX_TOTAL_BYTES = 40 * 1024 * 1024
MIN_USEFUL_CHARS = 150

PDF_TYPES = {"application/pdf", "application/x-pdf"}
DOCX_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",  # some browsers send this for .docx
}
W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class ResumeExtractionError(AppError):
    status_code = 422
    code = "resume_extraction_failed"


@dataclass
class ExtractedResume:
    text: str
    file_type: str
    pages: int | None = None
    truncated: bool = False
    warnings: list[str] = field(default_factory=list)


def _clean(text: str) -> str:
    text = text.replace("\x00", " ").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def _finish(text: str, file_type: str, pages: int | None) -> ExtractedResume:
    text = _clean(text)
    warnings: list[str] = []
    truncated = len(text) > MAX_TEXT_CHARS
    if truncated:
        text = text[:MAX_TEXT_CHARS]
        warnings.append(f"The resume was longer than {MAX_TEXT_CHARS:,} characters and has been shortened.")
    if len(text) < MIN_USEFUL_CHARS:
        if file_type == "pdf":
            raise ResumeExtractionError(
                "We couldn't read text from this PDF. It may be a scanned image. "
                "Upload a text-based PDF or DOCX, or paste your resume instead.",
                code="resume_no_text",
            )
        raise ResumeExtractionError(
            "This document contains too little text to use. Paste your resume instead.", code="resume_no_text"
        )
    return ExtractedResume(
        text=text, file_type=file_type, pages=pages, truncated=truncated, warnings=warnings
    )


def _extract_pdf(data: bytes) -> ExtractedResume:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise ResumeExtractionError(
                "This PDF is password-protected. Remove the password or paste your resume instead.",
                code="resume_encrypted",
            )
        pages = len(reader.pages)
        if pages > MAX_PAGES:
            raise ResumeExtractionError(
                f"This PDF has {pages} pages; resumes are limited to {MAX_PAGES}.", code="resume_too_long"
            )
        parts: list[str] = []
        total = 0
        for page in reader.pages:
            chunk = page.extract_text() or ""
            parts.append(chunk)
            total += len(chunk)
            if total > MAX_TEXT_CHARS * 2:
                break
    except ResumeExtractionError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError, OSError) as exc:
        raise ResumeExtractionError(
            "This PDF couldn't be read. It may be damaged.", code="resume_corrupt"
        ) from exc
    return _finish("\n".join(parts), "pdf", pages)


def _extract_docx(data: bytes) -> ExtractedResume:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            infos = zf.infolist()
            if sum(i.file_size for i in infos) > MAX_DOCX_TOTAL_BYTES:
                raise ResumeExtractionError(
                    "This document is too large once unpacked.", code="resume_too_large"
                )
            try:
                info = zf.getinfo("word/document.xml")
            except KeyError as exc:
                raise ResumeExtractionError(
                    "This file isn't a valid Word document.", code="resume_corrupt"
                ) from exc
            if info.file_size > MAX_DOCX_XML_BYTES:
                raise ResumeExtractionError(
                    "This document is too large once unpacked.", code="resume_too_large"
                )
            xml = zf.read(info)
    except ResumeExtractionError:
        raise
    except (zipfile.BadZipFile, OSError) as exc:
        raise ResumeExtractionError("This file isn't a valid Word document.", code="resume_corrupt") from exc

    # Word documents never contain a DTD. Refusing any DTD or entity declaration removes the
    # entity-expansion attacks that make XML parsing of untrusted input unsafe.
    if b"<!DOCTYPE" in xml or b"<!ENTITY" in xml:
        raise ResumeExtractionError("This file isn't a valid Word document.", code="resume_corrupt")
    try:
        root = ElementTree.fromstring(xml)  # noqa: S314 - DTD/entities rejected above
    except ElementTree.ParseError as exc:
        raise ResumeExtractionError("This file isn't a valid Word document.", code="resume_corrupt") from exc

    lines: list[str] = []
    for para in root.iter(f"{W_NS}p"):
        texts = []
        for node in para.iter():
            if node.tag == f"{W_NS}t" and node.text:
                texts.append(node.text)
            elif node.tag == f"{W_NS}tab":
                texts.append(" ")
            elif node.tag == f"{W_NS}br":
                texts.append("\n")
        lines.append("".join(texts))
    return _finish("\n".join(lines), "docx", None)


def extract_resume(filename: str, content_type: str | None, data: bytes, max_bytes: int) -> ExtractedResume:
    name = (filename or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if not data:
        raise ResumeExtractionError("The uploaded file is empty.", code="resume_empty")
    if len(data) > max_bytes:
        raise ResumeExtractionError(
            f"The file is larger than {max_bytes // (1024 * 1024)} MB.", code="resume_too_large"
        )
    ctype = (content_type or "").split(";")[0].strip().lower()

    if ext == "pdf":
        if ctype and ctype not in PDF_TYPES:
            raise ResumeExtractionError("The file type doesn't match a PDF.", code="resume_unsupported_type")
        if not data.startswith(b"%PDF-"):
            raise ResumeExtractionError("This file isn't a valid PDF.", code="resume_corrupt")
        return _extract_pdf(data)
    if ext == "docx":
        if ctype and ctype not in DOCX_TYPES and ctype != "application/zip":
            raise ResumeExtractionError(
                "The file type doesn't match a Word document.", code="resume_unsupported_type"
            )
        if not data.startswith(b"PK\x03\x04"):
            raise ResumeExtractionError("This file isn't a valid Word document.", code="resume_corrupt")
        return _extract_docx(data)
    raise ResumeExtractionError(
        "Unsupported file type. Upload a PDF or DOCX, or paste your resume as text.",
        code="resume_unsupported_type",
    )
