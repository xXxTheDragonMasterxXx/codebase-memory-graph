"""Thin wrapper around the Relate embedded graph database.

Every Relate / Cypher detail lives in this one module, so the rest of the app
stays database-agnostic. Implemented against the documented ``relate-db`` Python
API (https://relatedb.ai/docs/reference/api/python).

Verified-against notes (check these if your installed Relate version differs):
- ``relate.connect(path)`` with a ``.rl`` path opens a single-file store.
- Writes are Cypher ``CREATE`` run through ``conn.execute(stmt, params)``.
- Vector search uses ``SEARCH f IN (VECTOR INDEX <name> FOR $qvec LIMIT $k)``.
  If your build requires an explicitly typed query vector, change the one call
  in ``similar()`` to ``FOR vector($qvec, <dim>, FLOAT32)``.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    import relate  # pip install relate-db
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "Relate is not installed. Run:  pip install relate-db\n"
        "Docs: https://relatedb.ai/docs/get-started/install"
    ) from exc

from .parser import FunctionNode


class GraphStore:
    """Open a Relate store and expose codebase-graph reads and writes."""

    def __init__(self, path: str, embed_dim: int, index_name: str,
                 similarity: str) -> None:
        self.embed_dim = embed_dim
        self.index_name = index_name
        self.similarity = similarity
        self.conn = relate.connect(path)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "GraphStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # --- transactions -----------------------------------------------------
    def begin(self) -> None:
        self.conn.autocommit = False

    def commit(self) -> None:
        self.conn.commit()
        self.conn.autocommit = True

    # --- writes -----------------------------------------------------------
    def add_file(self, path: str, imports: List[str]) -> None:
        self.conn.execute(
            "CREATE (file:File {path: $path, imports: $imports})",
            {"path": path, "imports": imports},
        )

    def add_function(self, fn: FunctionNode, embedding: List[float]) -> None:
        self.conn.execute(
            "MATCH (file:File {path: $file}) "
            "CREATE (f:Function {qualname: $qualname, name: $name, file: $file, "
            "lineno: $lineno, cls: $cls, docstring: $doc, source: $source, "
            f"embedding: vector($embedding, {self.embed_dim}, FLOAT32)}}) "
            "CREATE (f)-[:DEFINED_IN]->(file)",
            {
                "qualname": fn.qualname, "name": fn.name, "file": fn.file,
                "lineno": fn.lineno, "cls": fn.cls, "doc": fn.docstring,
                "source": fn.source, "embedding": embedding,
            },
        )

    def add_call_edges(self, caller_qualname: str, callee_names: List[str]) -> None:
        """Create a CALLS edge to every function matching each callee name.

        Name-based resolution: a call to ``add`` links to all functions named
        ``add``. Simple and transparent; good enough to demonstrate traversal.
        """
        for callee in callee_names:
            self.conn.execute(
                "MATCH (caller:Function {qualname: $caller}) "
                "MATCH (callee:Function {name: $callee}) "
                "WHERE caller <> callee "
                "CREATE (caller)-[:CALLS]->(callee)",
                {"caller": caller_qualname, "callee": callee},
            )

    # --- schema -----------------------------------------------------------
    def create_vector_index(self) -> None:
        # dim/similarity come from our own config constants (not user input),
        # so inlining them in the DDL is safe and avoids param-in-DDL issues.
        self.conn.execute(
            f"CREATE VECTOR INDEX {self.index_name} IF NOT EXISTS "
            "FOR (f:Function) ON (f.embedding) "
            "OPTIONS {indexConfig: {"
            f"`vector.dimensions`: {self.embed_dim}, "
            f"`vector.similarity_function`: '{self.similarity}'}}}}"
        )

    # --- reads ------------------------------------------------------------
    def callers(self, name: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            "MATCH (caller:Function)-[:CALLS]->(:Function {name: $name}) "
            "RETURN caller.qualname AS qualname, caller.name AS name, "
            "caller.file AS file, caller.lineno AS lineno "
            "ORDER BY file, lineno",
            {"name": name},
        )
        return [row.data() for row in cursor.fetchall()]

    def callees(self, name: str) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            "MATCH (:Function {name: $name})-[:CALLS]->(callee:Function) "
            "RETURN DISTINCT callee.qualname AS qualname, callee.name AS name, "
            "callee.file AS file ORDER BY file, name",
            {"name": name},
        )
        return [row.data() for row in cursor.fetchall()]

    def get_function_source(self, name: str) -> Optional[str]:
        cursor = self.conn.execute(
            "MATCH (f:Function {name: $name}) RETURN f.source AS source LIMIT 1",
            {"name": name},
        )
        row = cursor.fetchone()
        return row["source"] if row else None

    def similar(self, qvec: List[float], k: int) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            "MATCH (f:Function) "
            f"SEARCH f IN (VECTOR INDEX {self.index_name} FOR $qvec LIMIT $k) "
            "SCORE AS score "
            "RETURN f.name AS name, f.qualname AS qualname, f.file AS file, "
            "round(score, 4) AS score "
            "ORDER BY score DESC",
            {"qvec": qvec, "k": k},
        )
        return [row.data() for row in cursor.fetchall()]

    def stats(self) -> Dict[str, int]:
        def count(cypher: str) -> int:
            return int(self.conn.execute(cypher).single()["c"])

        return {
            "files": count("MATCH (f:File) RETURN count(f) AS c"),
            "functions": count("MATCH (f:Function) RETURN count(f) AS c"),
            "calls": count("MATCH ()-[r:CALLS]->() RETURN count(r) AS c"),
        }
