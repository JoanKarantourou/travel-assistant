import re
from dataclasses import dataclass
from pathlib import Path

import pypdf

_Q_SPLIT = re.compile(r"Q\s*:", re.IGNORECASE)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_MAX_CHUNK_CHARS = 800


@dataclass
class Chunk:
    source: str
    page: int
    chunk_index: int
    content: str


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _split_sentences(text: str, max_len: int) -> list[str]:
    sentences = _SENTENCE_END.split(text)
    result: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = (current + " " + sentence).strip() if current else sentence
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                result.append(current)
            current = sentence[:max_len]
    if current:
        result.append(current)
    return result


def _locate_page(probe: str, pages: list[tuple[int, str]]) -> int:
    needle = re.sub(r"\s+", "", probe[:40]).lower()
    for page_num, text in pages:
        if needle in re.sub(r"\s+", "", text).lower():
            return page_num
    return pages[0][0] if pages else 1


def chunk_pdf(path: Path) -> list[Chunk]:
    reader = pypdf.PdfReader(str(path))
    pages = [(i + 1, _normalize(p.extract_text() or "")) for i, p in enumerate(reader.pages)]
    full_text = " ".join(text for _, text in pages)

    parts = _Q_SPLIT.split(full_text)
    # parts[0] is preamble (section headers before first Q:) - discard

    chunks: list[Chunk] = []
    chunk_index = 0

    for part in parts[1:]:
        content = _normalize(f"Q: {part}")
        if not content or content == "Q:":
            continue

        page_num = _locate_page(content, pages)

        if len(content) <= _MAX_CHUNK_CHARS:
            chunks.append(
                Chunk(
                    source=path.name,
                    page=page_num,
                    chunk_index=chunk_index,
                    content=content,
                )
            )
            chunk_index += 1
        else:
            for sub in _split_sentences(content, _MAX_CHUNK_CHARS):
                chunks.append(
                    Chunk(
                        source=path.name,
                        page=page_num,
                        chunk_index=chunk_index,
                        content=sub,
                    )
                )
                chunk_index += 1

    return chunks
