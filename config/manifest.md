# config Manifest

## Purpose
Holds configuration templates and overrides for local development and deployment.

## Contents
- `.env.example`: Sample environment variables covering Telegram tokens, admin IDs, booking endpoints, and browser pool sizing. Copy to `.env` (ignored) and fill with real credentials.

## Operational Notes
- Production secrets should live in environment variables or vault tooling; do not store actual `.env` files in Git.
- When adding new required settings, update `.env.example` and document the change in `docs/`.
