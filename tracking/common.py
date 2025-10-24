"""Shared utilities for tracking scripts."""

from __future__ import annotations

import ast
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Set

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_DEFAULT_EXCLUDED_DIRS = {".git", "__pycache__", "venv", ".venv", "tracking"}
_DEFAULT_EXCLUDED_FILES = {
    PROJECT_ROOT / "tracking" / "runtime.py",
    PROJECT_ROOT / "tracking" / "__init__.py",
}


def iter_python_files(
    root: Path,
    *,
    extra_excluded_dirs: Optional[Iterable[str]] = None,
    extra_excluded_files: Optional[Iterable[Path]] = None,
) -> Iterator[Path]:
    """Yield Python files beneath ``root`` honouring standard exclusions."""

    excluded_dirs: Set[str] = set(_DEFAULT_EXCLUDED_DIRS)
    if extra_excluded_dirs:
        excluded_dirs.update(extra_excluded_dirs)

    excluded_files = set(_DEFAULT_EXCLUDED_FILES)
    if extra_excluded_files:
        excluded_files.update(extra_excluded_files)

    for path in sorted(root.rglob("*.py")):
        if any(part in excluded_dirs for part in path.parts):
            continue
        if path in excluded_files:
            continue
        yield path


class ScopedNodeVisitor(ast.NodeVisitor):
    """Node visitor that tracks lexical scope for classes and functions."""

    def __init__(self) -> None:
        super().__init__()
        self.scope: List[str] = []

    @contextmanager
    def scoped(self, node: ast.AST) -> Iterator[None]:
        name = getattr(node, "name", "<lambda>")
        self.scope.append(name)
        try:
            yield
        finally:
            self.scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # type: ignore[override]
        self.scope.append(node.name)
        try:
            self.handle_class(node)
        finally:
            self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # type: ignore[override]
        self.handle_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # type: ignore[override]
        self.handle_async_function(node)

    def handle_class(self, node: ast.ClassDef) -> None:
        self.generic_visit(node)

    def handle_function(self, node: ast.AST) -> None:
        with self.scoped(node):
            self.generic_visit(node)

    def handle_async_function(self, node: ast.AST) -> None:
        self.handle_function(node)


DEFAULT_EXCLUDED_DIRS = frozenset(_DEFAULT_EXCLUDED_DIRS)
DEFAULT_EXCLUDED_FILES = frozenset(_DEFAULT_EXCLUDED_FILES)
