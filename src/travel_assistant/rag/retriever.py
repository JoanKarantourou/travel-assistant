from dataclasses import dataclass

from sentence_transformers import SentenceTransformer

from travel_assistant.persistence.database import get_session
from travel_assistant.persistence.repositories import nearest_faq_chunks

_MODEL_NAME = "all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None


@dataclass
class FAQResult:
    content: str
    source: str
    page: int
    score: float


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


async def search_faqs(query: str, k: int = 4) -> list[FAQResult]:
    embedding = _get_model().encode(query).tolist()
    async with get_session() as session:
        rows = await nearest_faq_chunks(session, embedding, k)
    return [
        FAQResult(content=chunk.content, source=chunk.source, page=chunk.page, score=score)
        for chunk, score in rows
    ]
