from pathlib import Path

import pytest

from travel_assistant.rag.chunker import _Q_SPLIT, Chunk, _normalize, _split_sentences, chunk_pdf

_FAQ_PDF = Path("src/travel_assistant/data/faqs.pdf")


def _skip_if_missing():
    if not _FAQ_PDF.exists():
        pytest.skip("faqs.pdf not present")


def test_chunks_are_returned():
    _skip_if_missing()
    chunks = chunk_pdf(_FAQ_PDF)
    assert len(chunks) > 0


def test_every_chunk_starts_with_q():
    _skip_if_missing()
    chunks = chunk_pdf(_FAQ_PDF)
    for chunk in chunks:
        assert chunk.content.startswith("Q:"), f"unexpected start: {chunk.content[:40]!r}"


def test_chunks_within_max_length():
    _skip_if_missing()
    chunks = chunk_pdf(_FAQ_PDF)
    for chunk in chunks:
        assert len(chunk.content) <= 800, f"chunk too long ({len(chunk.content)})"


def test_chunk_indices_unique_per_source():
    _skip_if_missing()
    chunks = chunk_pdf(_FAQ_PDF)
    keys = [(c.source, c.chunk_index) for c in chunks]
    assert len(keys) == len(set(keys))


def test_chunk_pages_are_positive():
    _skip_if_missing()
    chunks = chunk_pdf(_FAQ_PDF)
    for chunk in chunks:
        assert chunk.page >= 1


def test_split_sentences_respects_max():
    long_text = "This is sentence one. " * 50
    parts = _split_sentences(long_text, 100)
    for part in parts:
        assert len(part) <= 100


def test_split_sentences_preserves_content():
    text = "First sentence. Second sentence. Third sentence."
    parts = _split_sentences(text, 200)
    assert "".join(parts).replace(" ", "") == text.replace(" ", "")


def test_synthetic_chunks():
    raw = "Intro text Q: What is X? A: X is a thing. Q: What is Y? A: Y is another thing."
    parts = _Q_SPLIT.split(_normalize(raw))
    chunks = [Chunk("test.pdf", 1, i, f"Q: {p.strip()}") for i, p in enumerate(parts[1:])]
    assert len(chunks) == 2
    assert chunks[0].content.startswith("Q: What is X?")
    assert chunks[1].content.startswith("Q: What is Y?")
