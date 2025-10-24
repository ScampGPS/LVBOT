"""Developer utility to refresh tracking data and run the unit test suite."""

from __future__ import annotations
from tracking import t

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> int:
    """Run a subprocess relative to the project root."""

    t("scripts.run_checks._run")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


def refresh_tracking() -> int:
    """Update `tracking/all_functions.txt` using the module inventory."""

    t("scripts.run_checks.refresh_tracking")
    return _run([sys.executable, "-m", "tracking.inventory"])


def run_tests() -> int:
    """Execute the unit test suite."""

    t("scripts.run_checks.run_tests")
    return _run([sys.executable, "-m", "pytest"])


def main() -> None:
    """Refresh tracking inventory and run unit tests."""

    t("scripts.run_checks.main")
    steps = (
        ("tracking inventory", refresh_tracking),
        ("unit tests", run_tests),
    )

    for label, func in steps:
        print(f"→ Running {label}...")
        if func() != 0:
            print(f"✗ {label} failed")
            sys.exit(1)
        print(f"✓ {label} complete")

    print("All checks passed.")


if __name__ == "__main__":
    main()
