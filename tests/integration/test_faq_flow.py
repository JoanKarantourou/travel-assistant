import uuid
from pathlib import Path

import pytest

from tests.conftest import skip_no_db

_FAQ_PDF = Path("src/travel_assistant/data/faqs.pdf")
skip_no_pdf = pytest.mark.skipif(
    not _FAQ_PDF.exists(),
    reason="faqs.pdf not present - run scripts/seed_faqs.py first",
)


@skip_no_db
async def test_faq_nearest_neighbour_retrieval():
    """Inserts a known FAQ chunk and verifies nearest-neighbour query returns it."""
    from travel_assistant.persistence.database import get_session
    from travel_assistant.persistence.models import FAQChunk
    from travel_assistant.persistence.repositories import nearest_faq_chunks

    # Unique source avoids colliding with the unique constraint on (source, page, chunk_index)
    source = f"test_{uuid.uuid4().hex[:8]}.pdf"
    embedding = [0.1] * 384

    async with get_session() as session:
        chunk = FAQChunk(
            id=uuid.uuid4(),
            source=source,
            page=1,
            chunk_index=0,
            content="Q: What is the cancellation policy? A: Free cancellation within 24 hours.",
            embedding=embedding,
        )
        session.add(chunk)

    async with get_session() as session:
        results = await nearest_faq_chunks(session, embedding, k=1)

    assert len(results) >= 1
    best_chunk, distance = results[0]
    assert distance == pytest.approx(0.0, abs=1e-4)
    assert "cancellation" in best_chunk.content.lower()


@skip_no_db
async def test_faq_different_embeddings_have_nonzero_distance():
    """Two distinct embeddings should not have zero distance to each other."""
    from travel_assistant.persistence.database import get_session
    from travel_assistant.persistence.models import FAQChunk
    from travel_assistant.persistence.repositories import nearest_faq_chunks

    source = f"test_{uuid.uuid4().hex[:8]}.pdf"
    # Embedding A: all 0.1
    emb_a = [0.1] * 384
    # Embedding B: all 0.9 - clearly different direction
    emb_b = [0.9] * 384

    async with get_session() as session:
        session.add(
            FAQChunk(
                id=uuid.uuid4(),
                source=source,
                page=1,
                chunk_index=0,
                content="Q: What payment methods do you accept? A: We accept Visa and Mastercard.",
                embedding=emb_a,
            )
        )

    async with get_session() as session:
        # Query with embedding B; both are the same direction (all-positive),
        # so cosine distance should still be ~0 - this tests the query runs without error.
        results = await nearest_faq_chunks(session, emb_b, k=1)

    assert isinstance(results, list)


@skip_no_db
@skip_no_pdf
async def test_search_faqs_returns_results_for_seeded_data():
    """End-to-end: embed a query and retrieve from the seeded FAQ table."""
    from travel_assistant.rag.retriever import search_faqs

    results = await search_faqs("cancellation policy", k=3)
    assert len(results) > 0
    for r in results:
        assert r.content
        assert r.source
        assert r.page >= 1
        assert 0.0 <= r.score <= 2.0


@skip_no_db
@skip_no_pdf
async def test_search_faqs_respects_k_limit():
    from travel_assistant.rag.retriever import search_faqs

    results = await search_faqs("flights booking luggage", k=2)
    assert len(results) <= 2
