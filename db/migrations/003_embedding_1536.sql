-- Narralytica: Migrate embeddings from 768-dim to 1536-dim
-- Model change: gemini-embedding-001 → text-embedding-004
-- All existing embeddings must be re-generated after this migration.

-- Drop the old IVFFlat index (can't alter vector dimensions with index in place)
DROP INDEX IF EXISTS idx_scenes_embedding;

-- Null out existing embeddings first (768-dim data can't be cast to 1536-dim)
UPDATE scenes SET description_embedding = NULL;

-- Now alter the column to the new dimension
ALTER TABLE scenes ALTER COLUMN description_embedding TYPE vector(1536);

-- Recreate the index with new dimensions
-- Using HNSW instead of IVFFlat for better search quality at small-to-medium scale
CREATE INDEX idx_scenes_embedding ON scenes USING hnsw (description_embedding vector_cosine_ops);
