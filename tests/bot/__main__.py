"""CLI for exercising bot scenarios without Telegram."""

from __future__ import annotations

import argparse
from datetime import datetime
from typing import Optional

from .scenarios import queue_booking_flow


def _parse_date(value: Optional[str]):
    if value is None:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _safe_print(payload: str) -> None:
    try:
        print(payload)
    except UnicodeEncodeError:
        print(payload.encode('ascii', 'replace').decode('ascii'))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run conversational bot scenarios headlessly")
    subparsers = parser.add_subparsers(dest="scenario", required=True)

    queue_parser = subparsers.add_parser("queue-booking", help="Simulate the queue booking happy path")
    queue_parser.add_argument("--date", help="Target date in YYYY-MM-DD (defaults to three days from today)")
    queue_parser.add_argument("--time", default="09:00", help="Desired time slot, defaults to 09:00")
    queue_parser.add_argument(
        "--court",
        default="queue_court_all",
        help="Court callback identifier (e.g. queue_court_1 or queue_court_all)",
    )
    queue_parser.add_argument(
        "--queue-path",
        help="Optional reservation queue JSON path (defaults to temporary harness storage)",
    )

    args = parser.parse_args()

    if args.scenario == "queue-booking":
        records = queue_booking_flow(
            target_date=_parse_date(args.date),
            target_time=args.time,
            court_callback=args.court,
            queue_path=args.queue_path,
        )
        for idx, record in enumerate(records, start=1):
            action = record.get("action")
            text = record.get("text")
            _safe_print(f"[{idx}] {action}")
            if text:
                _safe_print(text)
            if record.get("kwargs"):
                _safe_print(f"    kwargs: {record['kwargs']}")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
