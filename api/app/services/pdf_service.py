from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_text_pages_from_path(path: Path) -> list[tuple[int | None, str]]:
    if path.suffix.lower() in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return [(1, text)]

    try:
        reader = PdfReader(str(path))
        pages = [
            (index, (page.extract_text() or "").strip())
            for index, page in enumerate(reader.pages, start=1)
        ]
        non_empty_pages = [(page_number, text) for page_number, text in pages if text]
        if non_empty_pages:
            return non_empty_pages
    except Exception:
        pass

    fallback_text = path.read_text(encoding="utf-8", errors="ignore")
    return [(1, fallback_text)]


def extract_text_from_path(path: Path) -> tuple[str, bool]:
    pages = extract_text_pages_from_path(path)
    text = "\n\n".join(page_text for _, page_text in pages if page_text).strip()
    ocr_required = len(text.strip()) < 120
    return text, ocr_required
