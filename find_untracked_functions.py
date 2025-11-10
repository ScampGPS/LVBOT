#!/usr/bin/env python3
"""Find all functions missing t() tracking calls."""
from tracking import t

import ast
import sys
from pathlib import Path
from typing import Set, List, Tuple

def get_function_name(node, class_name=None):
    """Get the full qualified name of a function."""
    t('find_untracked_functions.get_function_name')
    if class_name:
        return f"{class_name}.{node.name}"
    return node.name

def has_tracking_call(node) -> bool:
    """Check if function has a t() call at the start."""
    t('find_untracked_functions.has_tracking_call')
    if not node.body:
        return False

    # Check first few statements (allow docstring before t())
    for i, stmt in enumerate(node.body[:3]):
        # Skip docstrings
        if i == 0 and isinstance(stmt, ast.Expr) and isinstance(stmt.value, (ast.Str, ast.Constant)):
            continue

        # Look for t() call
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            if isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == 't':
                return True

        # If we hit any other statement, tracking call should have been found
        if not isinstance(stmt, ast.Expr):
            break

    return False

def analyze_file(filepath: Path) -> List[Tuple[str, int]]:
    """Analyze a Python file for functions missing t() calls."""
    t('find_untracked_functions.analyze_file')
    try:
        content = filepath.read_text(encoding='utf-8')
        tree = ast.parse(content, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    # Check if file imports tracking
    has_tracking_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == 'tracking' and any(alias.name == 't' for alias in node.names):
                has_tracking_import = True
                break

    if not has_tracking_import:
        return []  # Skip files that don't import tracking

    missing = []

    # Only check top-level functions and methods, not nested functions
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip private functions (but allow __init__)
            if node.name.startswith('_') and node.name != '__init__':
                continue

            if not has_tracking_call(node):
                missing.append((node.name, node.lineno))

        elif isinstance(node, ast.ClassDef):
            class_name = node.name
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Skip private methods (but allow __init__ and __post_init__)
                    if item.name.startswith('_') and item.name not in ['__init__', '__post_init__']:
                        continue

                    full_name = f"{class_name}.{item.name}"
                    if not has_tracking_call(item):
                        missing.append((full_name, item.lineno))

    return missing

def main():
    t('find_untracked_functions.main')
    root = Path('.')
    python_files = list(root.rglob('*.py'))

    all_missing = {}

    for filepath in python_files:
        # Skip venv, __pycache__, etc.
        if any(part.startswith('.') or part in ['venv', '__pycache__', 'node_modules']
               for part in filepath.parts):
            continue

        missing = analyze_file(filepath)
        if missing:
            all_missing[filepath] = missing

    # Print results
    if all_missing:
        print("Functions missing t() tracking calls:\n")
        for filepath, functions in sorted(all_missing.items()):
            print(f"\n{filepath}:")
            for func_name, lineno in functions:
                print(f"  Line {lineno}: {func_name}()")

        total = sum(len(funcs) for funcs in all_missing.values())
        print(f"\n\nTotal: {total} functions missing t() calls in {len(all_missing)} files")
    else:
        print("All functions have t() tracking calls!")

if __name__ == '__main__':
    main()
