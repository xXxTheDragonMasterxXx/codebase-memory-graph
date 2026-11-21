"""High-level, agent-facing queries that combine graph traversal with vectors.

These are the questions a coding agent actually asks its memory:
- ``callers`` / ``callees``  -> pure graph traversal (CALLS edges)
- ``similar``                -> vector search over function embeddings
- ``search``                 -> hybrid: semantic match, then graph expansion
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import config
from .embed import HashingEmbedder
from .store import GraphStore


def _open(store_path: str) -> GraphStore:
    return GraphStore(store_path, config.EMBED_DIM, config.VECTOR_INDEX,
                      config.SIMILARITY)


def callers(name: str, store_path: str = config.DEFAULT_STORE) -> List[Dict[str, Any]]:
    """Who calls ``name``? (incoming CALLS edges)"""
    with _open(store_path) as store:
        return store.callers(name)


def callees(name: str, store_path: str = config.DEFAULT_STORE) -> List[Dict[str, Any]]:
    """What does ``name`` call? (outgoing CALLS edges)"""
    with _open(store_path) as store:
        return store.callees(name)


def similar(name: str, k: int = 5,
            store_path: str = config.DEFAULT_STORE) -> Optional[List[Dict[str, Any]]]:
    """Functions whose implementation resembles ``name`` (vector search)."""
    with _open(store_path) as store:
        source = store.get_function_source(name)
        if source is None:
            return None
        qvec = HashingEmbedder(config.EMBED_DIM).embed(source)
        hits = store.similar(qvec, k + 1)  # +1 to drop the function itself
        return [hit for hit in hits if hit["name"] != name][:k]


def search(text: str, k: int = 5,
           store_path: str = config.DEFAULT_STORE) -> List[Dict[str, Any]]:
    """Hybrid recall: semantic match on ``text``, each hit expanded with its
    callers and callees — the connected context an agent needs to act.
    """
    with _open(store_path) as store:
        qvec = HashingEmbedder(config.EMBED_DIM).embed(text)
        hits = store.similar(qvec, k)
        for hit in hits:
            hit["callers"] = [c["qualname"] for c in store.callers(hit["name"])]
            hit["callees"] = [c["name"] for c in store.callees(hit["name"])]
        return hits
