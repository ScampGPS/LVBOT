# logs Manifest

## Purpose
Runtime log sink for the bot and automation stack. Files and subdirectories here capture telemetry, debug traces, and screenshots generated during execution.

## Layout
- `latest_log/`: Rolling directory that the bot rewrites with the most recent session output. Contents vary by run and may include text logs, JSON snapshots, or screenshots.

## Operational Notes
- Log content is transient; rotate or archive externally if you need long-term retention.
- This manifest is tracked via a `.gitignore` exception so documentation stays versioned while log output remains ignored.
