# Bot Refactor Plan

## Architecture Direction
- Extract a dedicated application shell: move Telegram-specific wiring out of `botapp/app.py` into `botapp/runtime/bot_application.py` (new `BotApplication` that only knows about handlers). `CleanBot` becomes a thin façade delegating to this runtime.
- Introduce a dependency container in `botapp/bootstrap/container.py` that composes `browser_pool`, `reservation_service`, `availability_checker`, etc., instead of instantiating them inline (`botapp/app.py:72-96`). Accept injectable factories so tests and alternative front-ends (CLI, HTTP) can reuse the same components.
- Create a lifecycle controller under `botapp/runtime/lifecycle.py` to own `_post_init`, `_post_stop`, `_graceful_shutdown`, metrics loop, and browser cleanup (`botapp/app.py:117-418`). `BotApplication` should request lifecycle services rather than mutate global state.
- Separate configuration by adding `botapp/config/__init__.py` with dataclasses for bot token, scheduler settings, and resource paths, replacing hard-coded constants like `BOT_TOKEN` and `BotConfig` defaults (`botapp/app.py:36-61`). Load from environment variables or files so other entry points can share them.

## Directory Restructure
```
botapp/
  app.py                  # becomes thin adapter that imports the new runner
  config/
    __init__.py           # config models + loader
  bootstrap/
    __init__.py
    container.py          # builds dependency graph
  runtime/
    __init__.py
    bot_application.py    # Telegram Application wiring
    lifecycle.py          # start/stop/metrics orchestration
    cli.py                # signal handling + main entry point
```
- Move signal/cleanup helpers (`botapp/app.py:402-475`) into `botapp/runtime/cli.py`, keeping `run_bot.py` as the CLI that calls `cli.main()`.
- Expose a booking façade (e.g., `automation/facade/booking_client.py`) for the fluent `browser.navigate(court)` API and wire it through the container so UI layers stay thin.

## Refactor Steps
1. Carve out configuration module, replacing direct constants with injected `AppConfig`; update `build_browser_resources` and `build_reservation_components` to accept config objects.
2. Implement `DependencyContainer` returning typed services (browser manager, reservation service, availability checker); update callers to use injected dependencies.
3. Port lifecycle methods into `LifecycleManager` exposing `startup()` / `shutdown()` async methods. `BotApplication` registers them with Telegram’s `post_init`/`post_stop`, while the CLI handles signals and delegates to lifecycle cleanup.
4. Shrink `CleanBot` to a thin adaptor or remove it; command handlers become standalone objects wired with injected services.
5. Update `register_core_handlers` to accept handler callables rather than the whole bot instance, reinforcing separation of concerns.

## Process Note
After completing this refactor, continue tracing the runtime flow to identify the next major module in need of restructuring. Repeat this review-refactor cycle until the entire codebase matches the modular, reusable design goals.
