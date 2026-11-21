"""Parse a Python repository into graph entities using the stdlib `ast`.

Produces plain dataclasses (no database coupling): the indexer turns these into
nodes and edges. Call resolution is name-based and intentionally simple — good
enough to demonstrate graph traversal; see README for the known limitation.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class FileNode:
    path: str
    imports: List[str] = field(default_factory=list)


@dataclass
class FunctionNode:
    qualname: str  # unique id, e.g. "pkg/mod.py::Class.method" or "pkg/mod.py::func"
    name: str
    file: str
    lineno: int
    cls: str  # defining class name, or "" for module-level functions
    docstring: str
    source: str
    calls: List[str] = field(default_factory=list)  # callee *names* (unresolved)


@dataclass
class ParsedRepo:
    files: List[FileNode]
    functions: List[FunctionNode]


def parse_repo(root: Path) -> ParsedRepo:
    """Walk every ``*.py`` file under ``root`` and extract files and functions."""
    files: List[FileNode] = []
    functions: List[FunctionNode] = []

    for py in sorted(root.rglob("*.py")):
        rel = py.relative_to(root).as_posix()
        try:
            source = py.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue  # skip files we cannot parse rather than aborting the build

        fnode = FileNode(path=rel)
        files.append(fnode)
        _collect_imports(tree, fnode)
        _collect_functions(tree, rel, source, cls="", out=functions)

    return ParsedRepo(files=files, functions=functions)


def _collect_imports(tree: ast.AST, fnode: FileNode) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            fnode.imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                fnode.imports.append(f"{module}.{alias.name}" if module else alias.name)


def _collect_functions(scope: ast.AST, rel: str, source: str, cls: str,
                       out: List[FunctionNode]) -> None:
    """Recursively collect function definitions, tracking the enclosing class."""
    for node in ast.iter_child_nodes(scope):
        if isinstance(node, ast.ClassDef):
            _collect_functions(node, rel, source, cls=node.name, out=out)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            prefix = f"{cls}." if cls else ""
            out.append(FunctionNode(
                qualname=f"{rel}::{prefix}{node.name}",
                name=node.name,
                file=rel,
                lineno=node.lineno,
                cls=cls,
                docstring=ast.get_docstring(node) or "",
                source=ast.get_source_segment(source, node) or "",
                calls=_extract_calls(node),
            ))
            # Nested functions keep the same class context as their parent.
            _collect_functions(node, rel, source, cls=cls, out=out)


def _extract_calls(func: ast.AST) -> List[str]:
    """Collect the names of functions called inside ``func`` (deduplicated)."""
    names: List[str] = []
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Name):
                names.append(target.id)
            elif isinstance(target, ast.Attribute):
                names.append(target.attr)
    return sorted(set(names))
