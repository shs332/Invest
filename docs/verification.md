# Verification

Base date: 2026-05-15 KST.

Canonical local check:

```bash
.venv/bin/python -m unittest discover -s tests
```

`uv` check, when the runner can access its cache:

```bash
uv run python -m unittest discover -s tests
```

Do not use `uv run pytest` for this repo unless `pytest` is added as a declared dev dependency. Current tests are `unittest`-native.

Network-fetch scripts may fail inside Codex sandbox before approval even when the script is correct. Re-run provider fetches with network approval or use existing cache artifacts under `data/cache/` when available.
