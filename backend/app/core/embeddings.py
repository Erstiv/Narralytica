"""
Narralytica: Embedding utility for search-time query embedding.

Uses Gemini text-embedding-004 (768 dims) to embed search queries.
The same model used at indexing time (generate_embeddings.py on M5 Mac).
"""
from google import genai
from app.core.config import settings

EMBEDDING_MODEL = "text-embedding-004"

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


async def embed_query(text: str) -> list[float]:
    """Generate a 768-dim embedding for a search query.

    Uses RETRIEVAL_QUERY task type (complementary to RETRIEVAL_DOCUMENT
    used at index time) for optimal search relevance.
    """
    client = _get_client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config={"task_type": "RETRIEVAL_QUERY"},
    )
    return result.embeddings[0].values
