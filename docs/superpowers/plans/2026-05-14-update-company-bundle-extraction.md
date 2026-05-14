# Update Company Bundle Extraction Plan

Goal: preserve the useful orchestration work left on `codex/bootstrap-invest-workspace` without reopening the broad bootstrap branch.

## Merged From Bootstrap

- Keep the `update_company_bundle.py` idea: one command fetches SEC companyfacts, normalizes financials, fetches price context, and builds a report bundle.
- Keep explicit bundle inputs so the bundle uses the artifacts produced by the current orchestration run instead of silently picking stale local files.
- Keep tests for child command ordering and price-fetch failure tolerance.

## Deliberately Not Merged

- Do not restore unsupported `fetch_price_snapshot.py --mode history`.
- Do not restore unsupported `normalize_financials.py --dated`.
- Do not restore generated raw/cache/report payloads to git.
- Do not merge the broad bootstrap branch directly.

## Verification

- `uv run python -m unittest tests.test_update_company_bundle -v`
- `uv run python -m unittest tests.test_skill_routing_policy -v`
- `uv run python -m unittest discover -s tests -v`
