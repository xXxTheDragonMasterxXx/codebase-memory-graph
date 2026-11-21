"""Central configuration constants.

Kept tiny and import-only so every module shares one source of truth for the
store location, embedding dimension and vector-index settings.
"""

# Single-file Relate store (.rl). Committed to the repo so judges can inspect it.
DEFAULT_STORE = "data/graph.rl"

# Embedding dimension. Must match the vector index config in the store.
EMBED_DIM = 128

# Vector index name and similarity function (Relate: 'cosine' or 'euclidean').
VECTOR_INDEX = "func_embedding"
SIMILARITY = "cosine"
