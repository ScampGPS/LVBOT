"""Lifecycle utilities for shutting down browser resources cleanly."""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import signal
import subprocess
from typing import Iterable, List, Optional, Tuple

from tracking import t

from .manager import BrowserManager, iter_active_managers, shutdown_active_managers

_DEFAULT_TIMEOUT = 30
_WINDOWS_PROCESS_NAMES = ('chrome', 'chromium', 'msedge', 'playwright')
_UNIX_PATTERNS = ('ms-playwright', 'playwright')


async def shutdown_browser_managers(
    *,
    logger: Optional[logging.Logger] = None,
    managers: Optional[Iterable[BrowserManager]] = None,
) -> bool:
    """Coroutine that attempts to stop the provided managers."""

    t('automation.browser.lifecycle.shutdown_browser_managers')
    return await shutdown_active_managers(logger=logger, managers=managers)


def shutdown_browser_managers_blocking(
    *,
    logger: Optional[logging.Logger] = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> bool:
    """Synchronously stop any active browser managers.

    Creates a short-lived event loop to run the async shutdown if no loop is in
    place. Returns ``True`` if every manager completed without raising.
    """

    t('automation.browser.lifecycle.shutdown_browser_managers_blocking')

    active = tuple(iter_active_managers())
    if not active:
        return True

    log = logger or logging.getLogger('BrowserShutdown')

    async def _shutdown() -> bool:
        t('automation.browser.lifecycle.shutdown_browser_managers_blocking._shutdown')
        return await shutdown_browser_managers(logger=log, managers=active)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(asyncio.wait_for(_shutdown(), timeout))
        except asyncio.TimeoutError:
            log.warning(
                "Timed out after %s seconds waiting for browser shutdown", timeout
            )
            return False
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            asyncio.set_event_loop(None)
            loop.close()
    else:
        # Already inside an event loop; the caller should use the async API
        log.debug(
            "shutdown_browser_managers_blocking called while an event loop is running; "
            "returning False"
        )
        return False


def force_kill_browser_processes(*, logger: Optional[logging.Logger] = None) -> None:
    """Forcibly terminate known Chromium/Playwright processes."""

    t('automation.browser.lifecycle.force_kill_browser_processes')
    log = logger or logging.getLogger('BrowserShutdown')
    processes = _find_playwright_processes()
    if not processes:
        log.debug("No Playwright-managed browser processes found to force kill")
        return

    system = platform.system()
    errors = 0

    for pid, name in processes:
        try:
            if system == 'Windows':
                subprocess.run(
                    ['taskkill', '/F', '/PID', str(pid)],
                    capture_output=True,
                    check=False,
                )
            else:
                os.kill(pid, signal.SIGKILL)
            log.info("Force killed process %s (pid=%s)", name, pid)
        except Exception as exc:
            errors += 1
            log.warning("Failed to kill process %s (pid=%s): %s", name, pid, exc)

    if errors:
        log.warning("Force kill completed with %s errors", errors)


def shutdown_all_browser_processes(
    *,
    logger: Optional[logging.Logger] = None,
    timeout: int = _DEFAULT_TIMEOUT,
    force: bool | None = None,
) -> None:
    """Attempt graceful shutdown, optionally falling back to a forced kill."""

    t('automation.browser.lifecycle.shutdown_all_browser_processes')
    log = logger or logging.getLogger('BrowserShutdown')

    running_before = list_running_browser_processes(logger=log)
    if running_before:
        log.info(
            "Detected existing browser processes: %s", ", ".join(sorted(set(running_before)))
        )

    graceful = shutdown_browser_managers_blocking(logger=log, timeout=timeout)

    if not graceful:
        log.warning("Browser managers did not shut down cleanly; considering forced kill")

    running_after = list_running_browser_processes(logger=log)

    requested_force = force is True
    should_force = requested_force
    if not should_force:
        should_force = bool(running_after)
    if not should_force:
        should_force = os.getenv('FORCE_PLAYWRIGHT_KILL') == '1'

    if should_force:
        if running_after:
            log.info(
                "Force killing lingering browser processes: %s",
                ", ".join(sorted(set(running_after))),
            )
        else:
            log.debug("Force kill requested; terminating known browser processes")
        force_kill_browser_processes(logger=log)
    elif running_after:
        log.warning(
            "Browser processes still running but force kill disabled: %s",
            ", ".join(sorted(set(running_after))),
        )


def list_running_browser_processes(
    *, logger: Optional[logging.Logger] = None
) -> List[str]:
    """Return names of detected Playwright-managed browser processes."""

    t('automation.browser.lifecycle.list_running_browser_processes')
    _ = logger  # retained for API symmetry; logging handled in helper
    return [name for _, name in _find_playwright_processes()]


def _find_playwright_processes() -> List[Tuple[int, str]]:
    """Locate processes spawned by Playwright-managed Chromium binaries."""
    t('automation.browser.lifecycle._find_playwright_processes')

    system = platform.system()
    processes: List[Tuple[int, str]] = []

    if system == 'Windows':
        processes.extend(_find_playwright_processes_windows())
    else:
        processes.extend(_find_playwright_processes_unix())

    seen = {}
    for pid, name in processes:
        seen[pid] = name
    return [(pid, name) for pid, name in seen.items()]


def _find_playwright_processes_windows() -> List[Tuple[int, str]]:
    t('automation.browser.lifecycle._find_playwright_processes_windows')
    filters = ','.join(_WINDOWS_PROCESS_NAMES)
    command = (
        "Get-Process -Name "
        + filters
        + " -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -and $_.Path -like '*ms-playwright*' } | "
        "Select-Object Id,Name"
    )

    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command', command],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return []

    processes: List[Tuple[int, str]] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.lower().startswith('id'):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        name = parts[1]
        processes.append((pid, name))

    # Also capture any standalone playwright.exe instances
    extra_command = (
        "Get-Process -Name playwright -ErrorAction SilentlyContinue | Select-Object Id,Name"
    )
    try:
        extra_result = subprocess.run(
            ['powershell', '-NoProfile', '-Command', extra_command],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        extra_result = None
    if extra_result is not None:
        for line in extra_result.stdout.splitlines():
            line = line.strip()
            if not line or line.lower().startswith('id'):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                pid = int(parts[0])
            except ValueError:
                continue
            name = parts[1]
            processes.append((pid, name))

    return processes


def _find_playwright_processes_unix() -> List[Tuple[int, str]]:
    t('automation.browser.lifecycle._find_playwright_processes_unix')
    try:
        result = subprocess.run(
            ['ps', '-eo', 'pid=,comm=,args='],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return []

    processes: List[Tuple[int, str]] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pid_str, comm, args = line.split(None, 2)
        except ValueError:
            continue
        try:
            pid = int(pid_str)
        except ValueError:
            continue
        check_target = f"{comm} {args}".lower()
        if any(pattern in check_target for pattern in _UNIX_PATTERNS):
            processes.append((pid, comm))

    return processes
