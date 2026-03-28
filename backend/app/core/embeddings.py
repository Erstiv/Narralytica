"""
Narralytica: Embedding utility for search-time query embedding.

Uses Google text-embedding-004 (1,536 dims) to embed search queries.
The same model used at indexing time (generate_embeddings.py on processing server).
Stays in the Google ecosystem with multilingual support.
"""
from google import genai
from app.core.config import settings

EMBEDDING_MODEL = "gemini-embedding-001"
OUTPUT_DIMS = 1536

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


async def embed_query(text: str) -> list[float]:
    """Generate a 1536-dim embedding for a search query.

    Uses RETRIEVAL_QUERY task type (complementary to RETRIEVAL_DOCUMENT
    used at index time) for optimal search relevance.
    """
    client = _get_client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config={"task_type": "RETRIEVAL_QUERY", "output_dimensionality": OUTPUT_DIMS},
    )
    return result.embeddings[0].values
