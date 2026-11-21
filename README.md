# Codebase Memory Graph

Relationship-aware memory for coding agents — your repo as a queryable graph, built on [Relate](https://relatedb.ai).

## Use case

Coding agents keep re-reading files to answer the same structural questions:
*who calls this function? what would I break if I change it? where is the code
that does X?* Plain text search and vector-only RAG miss the **relationships** —
the call graph — that make those answers correct.

**Codebase Memory Graph** turns a Python repository into a graph in Relate:
functions and files as nodes, `CALLS`, `DEFINED_IN` and `IMPORTS` as edges, with
a vector embedding on every function. An agent (or you) then asks questions that
combine **graph traversal** with **semantic search** in one place — exactly the
"connected context" an agent needs before it edits code.

The relationships that matter:

- `(:Function)-[:CALLS]->(:Function)` — the call graph (impact analysis)
- `(:Function)-[:DEFINED_IN]->(:File)` — where code lives
- `f.embedding` (vector) — semantic similarity between functions

## How it uses Relate

- **Mode:** single file (`data/graph.rl`)
- **Why this mode:** the whole graph is one portable, committable artifact.
  Judges clone the repo and the populated store is already there to inspect — no
  server, no rebuild required. `.rl` is Relate's single-file store format.
- **What the graph models:** the static structure of a Python codebase —
  `File` and `Function` nodes, `CALLS` / `DEFINED_IN` relationships, and a
  per-function vector (`FLOAT32`) indexed with a Relate `VECTOR INDEX` for
  cosine similarity search.

Everything Relate-specific lives in one file: [`src/cmg/store.py`](src/cmg/store.py).
Writes are Cypher `CREATE`; reads are Cypher `MATCH` and `SEARCH ... IN (VECTOR
INDEX ...)`; the build runs inside a single transaction.

## Setup and run

**Prerequisites:** Python 3.9+ and the Relate Python package.

```bash
# 1. install
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .                                     # installs relate-db + the `cmg` command

# 2. build the graph from the bundled sample repo
cmg build examples/sample_repo

# 3. ask the graph (results print as JSON)
cmg ask callers add            # who calls add()?
cmg ask callees perimeter      # what does perimeter() call?
cmg ask similar square         # functions implemented like square()
cmg ask search "compute area of a shape"   # hybrid: semantic match + call context
cmg stats                      # node / edge counts
```

Point it at any Python project the same way: `cmg build /path/to/repo`.

### First result in one line

```bash
pip install -e . && cmg build examples/sample_repo && cmg ask callers add
```

## Where the data lives

The persistent Relate store is committed at **[`data/graph.rl`](data/graph.rl)**
(created by `cmg build`). It is a single file you can inspect with Relate's CLI
or the Python API — the graph is the deliverable, not just the code.

---

## What the graph looks like (sample repo)

```
main.py ── report ──> rectangle_area ──> multiply ──> add
                 └──> perimeter ───────> multiply
square_area ──> square ──> multiply
```

`cmg ask callers multiply` returns every function on the call graph that reaches
`multiply` directly; `cmg ask search "area"` finds the area functions by meaning
and hands back their callers and callees as connected context.

## Architecture

| File | Responsibility |
|------|----------------|
| `src/cmg/parser.py` | Python `ast` → `File` / `Function` entities + call names |
| `src/cmg/embed.py` | Deterministic hashing embeddings (no API key, offline) |
| `src/cmg/store.py` | **All Relate / Cypher access** (nodes, edges, vector index, queries) |
| `src/cmg/indexer.py` | Clean rebuild of the store from a repo |
| `src/cmg/queries.py` | Agent-facing queries: callers, callees, similar, hybrid search |
| `src/cmg/cli.py` | `build` / `stats` / `ask` commands, JSON output |

## Notes & known limitations

- **Embeddings:** the default `HashingEmbedder` is dependency-free and captures
  *lexical* similarity so the project runs on a clean clone. For *semantic*
  similarity, install `sentence-transformers` and plug it in behind the same
  `.embed()` interface (one swap in `embed.py`).
- **Call resolution** is name-based: a call to `add` links to every function
  named `add`. Transparent and good enough to demonstrate traversal; a full
  resolver (scopes, imports, methods) is the natural next step.
- **Relate API:** implemented against the documented `relate-db` Python API. If
  your installed Relate version needs an explicitly typed query vector for
  search, change the single call in `store.similar()` to
  `FOR vector($qvec, 128, FLOAT32)` — see the comment in that file.
