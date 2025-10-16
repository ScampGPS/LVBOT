# LVBot Architecture Plan (Refined)

This repository now separates active code from archived legacy assets under
`archive/`. For historical reports, experiments, and deprecated utilities refer
to the corresponding subfolders inside `archive/`.

Active code organization:

- `telegram/` – Telegram application entrypoint, handlers, UI helpers.
- `reservations/` – Queue dataclasses, services, and schedulers.
- `automation/` – Browser pools, availability parsing, executors, and related configuration.
- `users/` – User management and tier definitions.
- `infrastructure/` – Shared settings, persistence, and configuration helpers.
- `archive/` – Legacy scripts, tests, and documentation preserved for reference.

Future refactor work should extend these namespaces rather than reintroducing
a monolithic `utils` module. Add new compatibility shims only when absolutely necessary and
prefer targeted modules inside the packages above.
