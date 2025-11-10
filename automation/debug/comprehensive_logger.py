"""Comprehensive debug logging for booking flows.

Enable with environment variable:
    LV_COMPREHENSIVE_DEBUG=1
"""

from __future__ import annotations
from tracking import t

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.async_api import Page


class ComprehensiveLogger:
    """Comprehensive logging for debugging booking flows."""

    def __init__(self, enabled: Optional[bool] = None):
        t('automation.debug.comprehensive_logger.ComprehensiveLogger.__init__')
        if enabled is None:
            enabled = os.getenv("LV_COMPREHENSIVE_DEBUG", "").strip() == "1"

        self.enabled = enabled
        self.artifacts_dir = Path("logs/latest_log/comprehensive_debug")

        if self.enabled:
            self.artifacts_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n[COMPREHENSIVE DEBUG] Enabled - artifacts at: {self.artifacts_dir}")

        self.console_logs: List[Dict[str, Any]] = []
        self.network_logs: List[Dict[str, Any]] = []
        self._listeners_attached = False

    def attach_listeners(self, page: Page) -> None:
        """Attach all debug listeners to a page."""
        t('automation.debug.comprehensive_logger.ComprehensiveLogger.attach_listeners')
        if not self.enabled or self._listeners_attached:
            return

        print("[COMPREHENSIVE DEBUG] Attaching listeners...")

        # Console logs
        page.on("console", lambda msg: self.console_logs.append({
            "timestamp": datetime.now().isoformat(),
            "type": msg.type,
            "text": msg.text,
            "location": msg.location if hasattr(msg, 'location') else None
        }))

        # Page errors
        page.on("pageerror", lambda error: self.console_logs.append({
            "timestamp": datetime.now().isoformat(),
            "type": "pageerror",
            "text": str(error)
        }))

        # Network requests
        page.on("request", lambda request: self.network_logs.append({
            "timestamp": datetime.now().isoformat(),
            "type": "request",
            "url": request.url,
            "method": request.method,
            "resource_type": request.resource_type,
            "headers": dict(request.headers) if hasattr(request, 'headers') else {}
        }))

        # Network responses
        page.on("response", lambda response: self.network_logs.append({
            "timestamp": datetime.now().isoformat(),
            "type": "response",
            "url": response.url,
            "status": response.status,
            "status_text": response.status_text,
            "headers": dict(response.headers) if hasattr(response, 'headers') else {}
        }))

        # Request failures
        page.on("requestfailed", lambda request: self.network_logs.append({
            "timestamp": datetime.now().isoformat(),
            "type": "request_failed",
            "url": request.url,
            "method": request.method,
            "failure": request.failure
        }))

        self._listeners_attached = True
        print("[COMPREHENSIVE DEBUG] Listeners attached")

    async def capture_state(self, page: Page, step_name: str) -> None:
        """Capture comprehensive page state."""
        t('automation.debug.comprehensive_logger.ComprehensiveLogger.capture_state')
        if not self.enabled:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        prefix = f"{step_name}_{timestamp}"

        print(f"\n{'='*70}")
        print(f"[DEBUG CAPTURE] {step_name}")
        print(f"{'='*70}")

        try:
            # 1. Screenshot
            screenshot_path = self.artifacts_dir / f"{prefix}_screenshot.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"  ✓ Screenshot: {screenshot_path.name}")

            # 2. Full HTML
            html_content = await page.content()
            html_path = self.artifacts_dir / f"{prefix}_page.html"
            html_path.write_text(html_content, encoding='utf-8')
            print(f"  ✓ HTML: {html_path.name}")

            # 3. URL
            print(f"  ✓ URL: {page.url}")

            # 4. Iframes
            frames = page.frames
            print(f"  ✓ Frames: {len(frames)} detected")
            for i, frame in enumerate(frames):
                if frame.url != "about:blank":
                    try:
                        frame_html = await frame.content()
                        frame_path = self.artifacts_dir / f"{prefix}_iframe_{i}.html"
                        frame_path.write_text(frame_html, encoding='utf-8')
                        print(f"    → Iframe {i}: {frame.url[:60]} (saved)")
                    except Exception as e:
                        print(f"    → Iframe {i}: Could not capture ({e})")

            # 5. DOM State
            dom_state = await page.evaluate('''() => {
                return {
                    readyState: document.readyState,
                    title: document.title,
                    activeElement: document.activeElement?.tagName,
                    forms: document.forms.length,
                    scripts: document.scripts.length,
                    stylesheets: document.styleSheets.length,
                    hidden_inputs: document.querySelectorAll('input[type="hidden"]').length
                };
            }''')
            print(f"  ✓ DOM State: {json.dumps(dom_state)}")

            # 6. Form inspection
            try:
                forms = await page.evaluate('''() => {
                    return Array.from(document.forms).map(form => ({
                        action: form.action,
                        method: form.method,
                        enctype: form.enctype,
                        fields: form.elements.length,
                        id: form.id,
                        name: form.name
                    }));
                }''')
                if forms:
                    print(f"  ✓ Forms: {len(forms)} found")
                    for idx, form in enumerate(forms):
                        print(f"    → Form {idx}: {json.dumps(form)}")
            except Exception as e:
                print(f"  ✗ Forms: Could not inspect ({e})")

            # 7. Hidden elements
            try:
                hidden = await page.eval_on_selector_all(
                    '[type="hidden"]',
                    '(elements) => elements.map(el => ({ name: el.name, value: el.value?.substring(0, 30), id: el.id }))'
                )
                if hidden:
                    print(f"  ✓ Hidden inputs: {len(hidden)} found")
                    for h in hidden[:5]:  # Show first 5
                        print(f"    → {h}")
            except Exception:
                pass

            # 8. JavaScript errors
            js_errors = await page.evaluate('''() => {
                if (window.__errors) return window.__errors;
                return [];
            }''')
            if js_errors:
                print(f"  ✓ JS Errors: {len(js_errors)} captured")

        except Exception as e:
            print(f"  ✗ Capture error: {e}")

        print(f"{'='*70}\n")

    def save_logs(self) -> None:
        """Save collected logs to disk."""
        t('automation.debug.comprehensive_logger.ComprehensiveLogger.save_logs')
        if not self.enabled:
            return

        if self.console_logs:
            console_path = self.artifacts_dir / "console_logs.json"
            console_path.write_text(json.dumps(self.console_logs, indent=2), encoding='utf-8')
            print(f"[COMPREHENSIVE DEBUG] Console logs saved: {console_path}")

        if self.network_logs:
            network_path = self.artifacts_dir / "network_logs.json"
            network_path.write_text(json.dumps(self.network_logs, indent=2), encoding='utf-8')
            print(f"[COMPREHENSIVE DEBUG] Network logs saved: {network_path}")

    def print_summary(self) -> None:
        """Print summary of captured data."""
        t('automation.debug.comprehensive_logger.ComprehensiveLogger.print_summary')
        if not self.enabled:
            return

        print(f"\n{'='*70}")
        print(f"[COMPREHENSIVE DEBUG] SUMMARY")
        print(f"{'='*70}")
        print(f"Console messages: {len(self.console_logs)}")
        print(f"Network events: {len(self.network_logs)}")

        # Console errors
        errors = [log for log in self.console_logs if log['type'] in ('error', 'pageerror')]
        if errors:
            print(f"\n⚠️  Console Errors ({len(errors)}):")
            for err in errors[:5]:
                print(f"  - {err['text'][:100]}")

        # Failed requests
        failed = [log for log in self.network_logs if log['type'] == 'request_failed']
        if failed:
            print(f"\n⚠️  Failed Requests ({len(failed)}):")
            for req in failed[:5]:
                print(f"  - {req['url'][:80]}")

        print(f"{'='*70}\n")


# Singleton instance
_logger: Optional[ComprehensiveLogger] = None


def get_logger() -> ComprehensiveLogger:
    """Get or create the comprehensive logger singleton."""
    t('automation.debug.comprehensive_logger.get_logger')
    global _logger
    if _logger is None:
        _logger = ComprehensiveLogger()
    return _logger


__all__ = ["ComprehensiveLogger", "get_logger"]
