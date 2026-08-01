"""
Resume text extraction.

Deliberately stateless: callers hand in bytes, get back text, and nothing is
written to disk or to the database.
"""

import io
import logging

logger = logging.getLogger(__name__)

# Anything past this is almost certainly not a resume; keeps a malicious or
# accidental upload from pinning the event loop on PDF parsing.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

# Below this, extraction "succeeded" but produced nothing usable — normally a
# scanned/image-only PDF with no text layer.
MIN_USABLE_CHARS = 50


class ResumeParseError(Exception):
    """Raised when an upload cannot be turned into usable text."""


def extract_resume_text(filename: str, data: bytes) -> str:
    """Extract plain text from a .pdf or .txt upload."""
    if not data:
        raise ResumeParseError("The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ResumeParseError("File is too large — please upload a resume under 5 MB.")

    name = (filename or "").lower()
    if name.endswith(".pdf"):
        text = _extract_pdf(data)
    elif name.endswith(".txt"):
        text = _extract_txt(data)
    else:
        raise ResumeParseError("Unsupported file type — upload a PDF or .txt file.")

    text = text.strip()
    if len(text) < MIN_USABLE_CHARS:
        raise ResumeParseError(
            "Couldn't read any text from that file. If it's a scanned PDF, "
            "try a text-based export instead."
        )
    return text


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise ResumeParseError("PDF support is unavailable on the server.") from exc

    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        logger.warning(f"[resume] PDF parse failed: {exc}")
        raise ResumeParseError("That PDF couldn't be read — it may be corrupt or encrypted.") from exc

    return "\n".join(pages)


def _extract_txt(data: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ResumeParseError("That text file uses an unsupported encoding.")
