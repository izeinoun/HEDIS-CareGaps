"""Extract plain text + a page-offset map from an uploaded medical-record PDF.

The offset map (`[{page, start, end}]`) is what lets the downstream
`anchor_findings.py` report a page number for every evidence quote, so the
reviewer UI can jump to the exact sentence in the chart. We build the offsets by
concatenating per-page text with a "\n\n" separator, exactly matching the
convention `anchor_findings.offsets_from_pages` uses.
"""
from __future__ import annotations

import pdfplumber

PAGE_SEP = "\n\n"


def extract_pdf(path: str) -> tuple[str, list[dict], list[str]]:
    """Return (full_text, offsets, pages).

    - full_text: the whole chart concatenated (pages joined by "\n\n").
    - offsets:   [{page, start, end}] character ranges of each page in full_text.
    - pages:     the raw per-page text list.
    """
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")

    text_parts: list[str] = []
    offsets: list[dict] = []
    cursor = 0
    for i, page in enumerate(pages, start=1):
        start = cursor
        text_parts.append(page)
        cursor += len(page)
        offsets.append({"page": i, "start": start, "end": cursor})
        if i < len(pages):
            text_parts.append(PAGE_SEP)
            cursor += len(PAGE_SEP)
    return "".join(text_parts), offsets, pages


def extract_text_file(path: str) -> tuple[str, list[dict], list[str]]:
    """Fallback intake for a plain .txt chart (single logical page)."""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    return text, [{"page": 1, "start": 0, "end": len(text)}], [text]
