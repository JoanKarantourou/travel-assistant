"""FAQ ingestion pipeline: parse, embed, and upsert chunks into the database.

Reads the FAQ PDF, chunks it, generates embeddings with the same model used
for retrieval, and upserts each chunk into the ``faq_chunks`` table.
"""

from pathlib import Path

from sentence_transformers import SentenceTransformer
from sqlalchemy.dialects.postgresql import insert

from travel_assistant.persistence.database import get_session
from travel_assistant.persistence.models import FAQChunk
from travel_assistant.rag.chunker import chunk_pdf

_FAQ_PDF = Path(__file__).parent.parent / "data" / "faqs.pdf"
_MODEL_NAME = "all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Return the singleton sentence-transformer model, loading it on first call."""
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


async def run_ingest(path: Path = _FAQ_PDF) -> int:
    """Ingest *path* into the database and return the number of chunks upserted."""
    chunks = chunk_pdf(path)
    if not chunks:
        return 0

    model = _get_model()
    embeddings = model.encode([c.content for c in chunks], batch_size=32, show_progress_bar=False)

    async with get_session() as session:
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            # Upsert so re-running ingest after PDF edits refreshes content
            # without violating the unique constraint on (source, page, chunk_index).
            stmt = (
                insert(FAQChunk)
                .values(
                    source=chunk.source,
                    page=chunk.page,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    embedding=embedding.tolist(),
                )
                .on_conflict_do_update(
                    constraint="uq_faq_chunk",
                    set_={"content": chunk.content, "embedding": embedding.tolist()},
                )
            )
            await session.execute(stmt)

    return len(chunks)
