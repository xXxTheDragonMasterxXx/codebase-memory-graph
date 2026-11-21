"""Build a Relate graph from a Python repository.

Does a clean rebuild each time: the single-file store is removed and recreated,
so the committed graph always matches the current code. Nodes and relationships
are written inside one transaction for speed, then the vector index is created.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from . import config
from .embed import HashingEmbedder
from .parser import parse_repo
from .store import GraphStore


def build(repo_path: str, store_path: str = config.DEFAULT_STORE) -> Dict[str, int]:
    """Index ``repo_path`` into the Relate store and return node/edge counts."""
    repo = Path(repo_path).resolve()
    if not repo.exists():
        raise FileNotFoundError(f"Repo not found: {repo}")

    store_file = Path(store_path)
    if store_file.exists():
        store_file.unlink()  # clean rebuild
    store_file.parent.mkdir(parents=True, exist_ok=True)

    parsed = parse_repo(repo)
    embedder = HashingEmbedder(config.EMBED_DIM)

    with GraphStore(store_path, config.EMBED_DIM, config.VECTOR_INDEX,
                    config.SIMILARITY) as store:
        store.begin()
        for file_node in parsed.files:
            store.add_file(file_node.path, file_node.imports)
        for fn in parsed.functions:
            text = f"{fn.name} {fn.docstring} {fn.source}"
            store.add_function(fn, embedder.embed(text))
        for fn in parsed.functions:
            store.add_call_edges(fn.qualname, fn.calls)
        store.commit()

        store.create_vector_index()
        return store.stats()
