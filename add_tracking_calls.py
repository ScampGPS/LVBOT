#!/usr/bin/env python3
"""Automatically add t() tracking calls to functions missing them."""
from tracking import t

import ast
import sys
from pathlib import Path
from typing import List, Tuple, Dict

def get_module_path(filepath: Path) -> str:
    """Convert file path to module path for tracking string."""
    t('add_tracking_calls.get_module_path')
    # Remove .py extension and convert to module path
    parts = filepath.with_suffix('').parts

    # Remove leading '.' if present
    if parts and parts[0] == '.':
        parts = parts[1:]

    return '.'.join(parts)

def has_tracking_call(node) -> bool:
    """Check if function has a t() call at the start."""
    t('add_tracking_calls.has_tracking_call')
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

def analyze_file(filepath: Path) -> List[Tuple[str, int, str]]:
    """Analyze a Python file for functions missing t() calls.

    Returns list of (function_name, line_number, tracking_string) tuples.
    """
    t('add_tracking_calls.analyze_file')
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

    module_path = get_module_path(filepath)
    missing = []

    def process_function(node, class_name=None):
        """Process a function node and add to missing list if needed."""
        t('add_tracking_calls.analyze_file.process_function')
        # Skip private functions and special methods (except __init__ and __post_init__)
        if node.name.startswith('_') and node.name not in ['__init__', '__post_init__']:
            return

        if not has_tracking_call(node):
            func_name = node.name
            if class_name:
                tracking_str = f"{module_path}.{class_name}.{func_name}"
            else:
                tracking_str = f"{module_path}.{func_name}"

            missing.append((func_name, node.lineno, tracking_str))

    # Only check top-level functions and methods, not nested functions
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            process_function(node)
        elif isinstance(node, ast.ClassDef):
            class_name = node.name
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    process_function(item, class_name)

    return missing

def insert_tracking_call(filepath: Path, functions: List[Tuple[str, int, str]]) -> bool:
    """Insert t() calls into the file for the given functions.

    Returns True if file was modified, False otherwise.
    """
    t('add_tracking_calls.insert_tracking_call')
    try:
        lines = filepath.read_text(encoding='utf-8').splitlines(keepends=True)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False

    # Sort functions by line number in reverse order (so we modify from bottom to top)
    functions_sorted = sorted(functions, key=lambda x: x[1], reverse=True)

    modified = False
    for func_name, lineno, tracking_str in functions_sorted:
        # Line numbers are 1-indexed, list is 0-indexed
        func_line_idx = lineno - 1

        if func_line_idx >= len(lines):
            continue

        # Find the indentation of the function definition
        func_line = lines[func_line_idx]
        indent = len(func_line) - len(func_line.lstrip())
        body_indent = indent + 4  # Standard Python indentation

        # Find where to insert the t() call
        # We need to find the first line of the function body
        insert_idx = func_line_idx + 1

        # Skip past the docstring if present
        if insert_idx < len(lines):
            next_line = lines[insert_idx].strip()
            if next_line.startswith('"""') or next_line.startswith("'''"):
                # Multi-line docstring
                quote = '"""' if next_line.startswith('"""') else "'''"
                if not next_line.endswith(quote) or next_line.count(quote) < 2:
                    # Docstring spans multiple lines
                    insert_idx += 1
                    while insert_idx < len(lines):
                        if quote in lines[insert_idx]:
                            insert_idx += 1
                            break
                        insert_idx += 1
                else:
                    # Single-line docstring
                    insert_idx += 1

        # Create the t() call line
        tracking_call = f"{' ' * body_indent}t('{tracking_str}')\n"

        # Insert the tracking call
        lines.insert(insert_idx, tracking_call)
        modified = True

    if modified:
        try:
            filepath.write_text(''.join(lines), encoding='utf-8')
            return True
        except Exception as e:
            print(f"Error writing {filepath}: {e}")
            return False

    return False

def main():
    t('add_tracking_calls.main')
    print("Scanning for functions missing t() calls...\n")

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

    if not all_missing:
        print("All functions already have t() tracking calls!")
        return

    # Show what we found
    total = sum(len(funcs) for funcs in all_missing.values())
    print(f"Found {total} functions missing t() calls in {len(all_missing)} files\n")

    # Ask for confirmation
    response = input("Add t() calls to all these functions? [y/N]: ").strip().lower()
    if response != 'y':
        print("Aborted.")
        return

    # Process each file
    modified_count = 0
    for filepath, functions in all_missing.items():
        print(f"Processing {filepath}...")
        if insert_tracking_call(filepath, functions):
            modified_count += 1
            print(f"  ✓ Added {len(functions)} t() calls")
        else:
            print(f"  ✗ Failed to modify")

    print(f"\n✓ Modified {modified_count} files")
    print("\nRun find_untracked_functions.py again to verify all tracking calls were added.")

if __name__ == '__main__':
    main()
