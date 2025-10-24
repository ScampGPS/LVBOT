"""Add tracking calls to every Python function in the project."""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from tracking.common import (
    PROJECT_ROOT,
    ScopedNodeVisitor,
    iter_python_files,
)

TRACKING_IMPORT = "from tracking import t"

INCLUDE_TESTS_FLAG = "--include-tests"
INCLUDE_TESTS = INCLUDE_TESTS_FLAG in sys.argv
if INCLUDE_TESTS:
    sys.argv.remove(INCLUDE_TESTS_FLAG)
    EXTRA_EXCLUDED_DIRS = set()
else:
    EXTRA_EXCLUDED_DIRS = {"tests"}

EXTRA_EXCLUDED_FILES = {
    PROJECT_ROOT / "tracking" / "instrument.py",
}


@dataclass
class Edit:
    start: int
    end: int
    lines: List[str]


def _is_str_constant(node: Optional[ast.AST]) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def strip_newline(text: str) -> str:
    return text.rstrip("\n").rstrip("\r")


def indent_of(text: str) -> str:
    stripped_len = len(text.lstrip(" \t"))
    return text[: len(text) - stripped_len]


def detect_newline(lines: List[str]) -> str:
    for line in lines:
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith("\n"):
            return "\n"
    return "\n"


def already_tracked(node: ast.AST) -> bool:
    body = getattr(node, "body", []) or []
    has_docstring = (
        bool(body)
        and isinstance(body[0], ast.Expr)
        and _is_str_constant(getattr(body[0], "value", None))
    )
    first_index = 1 if has_docstring else 0
    if len(body) <= first_index:
        return False
    stmt = body[first_index]
    if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
        return False
    func = stmt.value.func
    if isinstance(func, ast.Name) and func.id == "t":
        return True
    return False


def docstring_node(node: ast.AST) -> Optional[ast.Expr]:
    body = getattr(node, "body", []) or []
    if not body:
        return None
    first = body[0]
    value = getattr(first, "value", None)
    if isinstance(first, ast.Expr) and _is_str_constant(value):
        return first
    return None


def add_import_if_needed(
    tree: ast.Module, edits: List[Edit], lines: List[str], newline: str
) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "tracking":
            for alias in node.names:
                if alias.name == "t" and alias.asname in (None, "t"):
                    return
    insert_line = 0
    body = tree.body
    index = 0
    if body and isinstance(body[0], ast.Expr):
        value = getattr(body[0], "value", None)
        if _is_str_constant(value):
            insert_line = getattr(body[0], "end_lineno", body[0].lineno)
            index = 1
    while index < len(body):
        node = body[index]
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            insert_line = getattr(node, "end_lineno", node.lineno)
            index += 1
            continue
        break
    edits.append(
        Edit(start=insert_line, end=insert_line, lines=[TRACKING_IMPORT + newline])
    )


class TrackingTransformer(ScopedNodeVisitor):
    def __init__(
        self, module: str, lines: List[str], newline: str, edits: List[Edit]
    ) -> None:
        super().__init__()
        self.module = module
        self.lines = lines
        self.newline = newline
        self.edits = edits
        self.added_tracking = False

    def handle_function(self, node: ast.FunctionDef) -> None:  # type: ignore[override]
        self._instrument(node)

    def handle_async_function(self, node: ast.AsyncFunctionDef) -> None:  # type: ignore[override]
        self._instrument(node)

    def _instrument(self, node: ast.AST) -> None:
        if already_tracked(node):
            # Continue walking to handle nested functions even if parent is tracked.
            with self.scoped(node):
                self.generic_visit(node)
            return

        self.added_tracking = True

        qualname_parts = [self.module] if self.module else []
        qualname_parts.extend(self.scope)
        qualname_parts.append(getattr(node, "name", "<lambda>"))
        qualname = ".".join(filter(None, qualname_parts))

        doc_node = docstring_node(node)
        node_body = getattr(node, "body", []) or []
        first_real_stmt = (
            node_body[1]
            if doc_node is not None and len(node_body) > 1
            else node_body[0] if node_body else None
        )
        def_line_index = getattr(node, "lineno", 1) - 1

        # Determine if the first executable statement shares the definition line (one-liner).
        body_starts_on_def_line = False
        first_stmt = first_real_stmt or doc_node
        if first_stmt is not None:
            start_line = getattr(first_stmt, "lineno", getattr(node, "lineno", 1))
            body_starts_on_def_line = start_line == getattr(node, "lineno", 1)

        track_call = f"t('{qualname}')"

        if doc_node is not None and getattr(doc_node, "lineno", 1) == getattr(
            node, "lineno", 1
        ):
            # Inline docstring on the definition line; rewrite definition into multi-line form.
            self._rewrite_inline_docstring(node, doc_node, track_call)
        elif body_starts_on_def_line and doc_node is None:
            # One-line function without docstring.
            self._rewrite_one_liner(node, track_call)
        else:
            if doc_node is not None:
                target_line = getattr(doc_node, "end_lineno", doc_node.lineno)
                insert_index = target_line
                indent_line = (
                    strip_newline(self.lines[target_line - 1])
                    if target_line - 1 < len(self.lines)
                    else ""
                )
            elif first_real_stmt is not None:
                target_line = getattr(first_real_stmt, "lineno", node.lineno)
                insert_index = target_line - 1
                indent_line = (
                    strip_newline(self.lines[insert_index])
                    if insert_index < len(self.lines)
                    else ""
                )
            else:
                # Function has no body (should not happen), insert a pass.
                indent_line = (
                    strip_newline(self.lines[def_line_index])
                    if def_line_index < len(self.lines)
                    else ""
                )
                insert_index = def_line_index + 1
                self.edits.append(
                    Edit(
                        start=insert_index,
                        end=insert_index,
                        lines=[indent_of(indent_line) + "    pass" + self.newline],
                    )
                )
            indent = (
                indent_of(indent_line)
                if indent_line
                else indent_of(strip_newline(self.lines[def_line_index])) + "    "
            )
            self.edits.append(
                Edit(
                    start=insert_index,
                    end=insert_index,
                    lines=[indent + track_call + self.newline],
                )
            )

        with self.scoped(node):
            self.generic_visit(node)

    def _rewrite_one_liner(self, node: ast.AST, track_call: str) -> None:
        def_line_index = getattr(node, "lineno", 1) - 1
        if def_line_index >= len(self.lines):
            return
        line = self.lines[def_line_index]
        stripped = strip_newline(line)
        colon_pos = stripped.find(":")
        if colon_pos == -1:
            return
        indent = indent_of(stripped)
        body_indent = indent + "    "
        rest = stripped[colon_pos + 1 :]
        rest_line = rest.lstrip(" \t")
        rest_prefix = body_indent + rest_line if rest_line else None
        new_lines = [
            stripped[: colon_pos + 1] + self.newline,
            body_indent + track_call + self.newline,
        ]
        if rest_line:
            new_lines.append(rest_prefix + self.newline)
        self.edits.append(
            Edit(start=def_line_index, end=def_line_index + 1, lines=new_lines)
        )

    def _rewrite_inline_docstring(
        self, node: ast.AST, doc_node: ast.Expr, track_call: str
    ) -> None:
        def_line_index = getattr(node, "lineno", 1) - 1
        if def_line_index >= len(self.lines):
            return
        original_line = strip_newline(self.lines[def_line_index])
        colon_pos = original_line.find(":")
        if colon_pos == -1:
            return
        indent = indent_of(original_line)
        body_indent = indent + "    "
        doc_value = ast.get_docstring(node, clean=False) or ""
        doc_literal = repr(doc_value)
        if doc_value and "\n" in doc_value:
            doc_literal = '"""' + doc_value.replace('"""', '"""') + '"""'
        new_lines = [
            original_line[: colon_pos + 1] + self.newline,
            body_indent + doc_literal + self.newline,
            body_indent + track_call + self.newline,
        ]
        self.edits.append(
            Edit(start=def_line_index, end=def_line_index + 1, lines=new_lines)
        )


def apply_edits(lines: List[str], edits: List[Edit]) -> List[str]:
    for edit in sorted(edits, key=lambda e: e.start, reverse=True):
        lines[edit.start : edit.end] = edit.lines
    return lines


def process_file(path: Path) -> bool:
    original_text = path.read_text(encoding="utf-8")
    lines = original_text.splitlines(keepends=True)
    newline = detect_newline(lines)
    try:
        tree = ast.parse(original_text, filename=str(path), type_comments=True)
    except SyntaxError as exc:
        print(f"Skipping {path}: failed to parse ({exc})")
        return False

    edits: List[Edit] = []
    module_name = ".".join(
        part
        for part in path.relative_to(PROJECT_ROOT).with_suffix("").parts
        if part != "__init__"
    )
    transformer = TrackingTransformer(module_name, lines, newline, edits)
    transformer.visit(tree)

    if not transformer.added_tracking:
        return False

    add_import_if_needed(tree, edits, lines, newline)

    updated_lines = apply_edits(lines, edits)
    updated_text = "".join(updated_lines)
    if updated_text != original_text:
        path.write_text(updated_text, encoding="utf-8")
        return True
    return False


def main(argv: List[str]) -> int:
    changed_any = False
    for file_path in iter_python_files(
        PROJECT_ROOT,
        extra_excluded_dirs=EXTRA_EXCLUDED_DIRS,
        extra_excluded_files=EXTRA_EXCLUDED_FILES,
    ):
        if process_file(file_path):
            print(f"Updated {file_path.relative_to(PROJECT_ROOT)}")
            changed_any = True
    if not changed_any:
        print("No files updated; tracking calls already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
