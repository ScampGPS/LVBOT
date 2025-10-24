"""Enumerate all function definitions in the codebase."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set

from tracking.common import (
    PROJECT_ROOT,
    ScopedNodeVisitor,
    iter_python_files,
)

OUTPUT_FILE = PROJECT_ROOT / "tracking" / "all_functions.txt"

EXTRA_EXCLUDED_FILES = {
    PROJECT_ROOT / "tracking" / "instrument.py",
    PROJECT_ROOT / "tracking" / "inventory.py",
}


@dataclass
class FunctionCollector(ScopedNodeVisitor):
    module: str
    functions: Set[str]

    def __post_init__(self) -> None:
        super().__init__()

    def handle_function(self, node: ast.FunctionDef) -> None:  # type: ignore[override]
        self._record(node)

    def handle_async_function(self, node: ast.AsyncFunctionDef) -> None:  # type: ignore[override]
        self._record(node)

    def _record(self, node: ast.AST) -> None:
        name = getattr(node, "name", None)
        if not name:
            return
        qualname_parts: List[str] = []
        if self.module:
            qualname_parts.append(self.module)
        qualname_parts.extend(self.scope)
        qualname_parts.append(name)
        self.functions.add(".".join(qualname_parts))

        with self.scoped(node):
            self.generic_visit(node)


def module_name_for(path: Path) -> str:
    return ".".join(
        part
        for part in path.relative_to(PROJECT_ROOT).with_suffix("").parts
        if part != "__init__"
    )


def collect_functions(path: Path) -> Set[str]:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(path), type_comments=True)
    except SyntaxError as exc:
        print(f"Skipping {path}: failed to parse ({exc})")
        return set()

    functions: Set[str] = set()
    collector = FunctionCollector(module=module_name_for(path), functions=functions)
    collector.visit(tree)
    return functions


def main() -> int:
    all_functions: Set[str] = set()
    for file_path in iter_python_files(
        PROJECT_ROOT,
        extra_excluded_files=EXTRA_EXCLUDED_FILES,
    ):
        all_functions.update(collect_functions(file_path))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        OUTPUT_FILE.unlink()
    except FileNotFoundError:
        pass
    with OUTPUT_FILE.open("w", encoding="utf-8") as handle:
        for name in sorted(all_functions):
            handle.write(f"{name}\n")
    print(
        f"Wrote {len(all_functions)} functions to {OUTPUT_FILE.relative_to(PROJECT_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
