# Post-mortem: dashboard showed "No data loaded" (2026-11-07)

**Status:** fixed and released to `main` (PR #4 into `staging`, PR #5 into `main`, 7 November 2026). Checked on a fresh clone of `main`.
**Format:** blameless; this is about the process, not people.

## Summary

The dashboard on `main` showed "No data loaded yet" on every data page. `main` had the app but none of the code that produces its data, and the data file the app reads is generated rather than committed. A second bug meant that even where the data did exist, a page opened before the data was built kept showing "no data" until the server restarted.

## Impact

- Anyone running the app from `main` (or a fresh clone of any branch) saw empty pages with only an instruction to run a command.
- No wrong numbers were shown. The failure was empty pages, not misleading data.
- Time affected: from PR #3 merging to `main` (15:58) until the fix reaches `main`.

## Timeline (2026-11-07, GMT)

| Time | Event |
|---|---|
| 15:47 | Environment and dashboard skeleton committed on a personal branch. The data pages had empty states because no loaders existed yet. |
| 15:56 | PR #2 (skeleton + evidence brief) merged into `staging`. |
| 15:58 | PR #3 merged `staging` into `main`. **`main` now has the app but no loaders.** |
| ~15:50-16:00 | Loaders, pipeline and charts written and tested on the local machine only (uncommitted). Locally the dashboard worked. |
| 16:00 | Local dashboard started at localhost:8501, showing data on that machine. |
| 16:05 | User reports the "no data" problem. |
| 16:09 | Fix committed (`f992a93`), checked on a fresh clone, PR #4 opened. |
| 16:27 | PR #5 merged `staging` into `main`. A fresh clone of `main` built its data in 34 seconds and showed charts. |

## Root causes

1. **The app shipped before its data code.** PR #2 contained a dashboard whose pages depend on `data/processed/indicators.parquet`, but the loaders that build that file came later and were never in that PR. Merging `staging` into `main` promoted a dashboard that could only ever be empty.
2. **The data file is generated, and nothing generated it automatically.** `data/processed/` is (correctly) not committed, to avoid stale data and merge conflicts between three people. But the only way to build it was a manual command (`uv run python -m ta_london.pipeline`), mentioned in the README and in a warning on the page. On a fresh clone that step is easy to miss.
3. **"No data" was cached.** `load_data()` was wrapped in `@st.cache_data`. If a page was opened before the file existed, the empty result was cached and kept being served after the file was built, until the server restarted.
4. **The tests passed because of local state.** The page tests ran on the developer machine, where the data file existed, and `test_processed_output.py` skips itself when the file is missing. No test simulated a fresh clone, so "works on my machine" was all the tests proved.
5. **Communication.** The work was described as "the dashboard draws real charts" while the loaders were still uncommitted. The caveat ("only on your machine") came last and was easy to miss.

## Fix

- The app now builds the data on first load if it is missing (`build_data_if_missing()` in `app/components.py`). It calls the pipeline in `src/`, so no cleaning logic moved into the app. It shows a spinner (about 30 seconds) and, if the build fails, the reason instead of a blank page. A lock stops two pages building at once.
- The cache is now keyed on the file's modification time, so a rebuilt file is picked up immediately, with no restart.
- Loaders, pipeline and charts are committed and in PR #4.

## Verification

- Fresh clone with no processed data: opening Home built the data automatically in 33 seconds, with no warnings, and the borough page drew its chart.
- New regression tests (`tests/test_app_data_loading.py`) cover: no data with auto-build off shows a clear message; no data triggers a build; a failed build shows its reason; a file created after a page loaded is shown without a restart.
- Full suite: 72 tests pass. `ruff check` and `ruff format --check` are clean.

## Follow-ups

| # | Action | Why |
|---|---|---|
| 1 | ~~Merge PR #4 into `staging`, then `staging` into `main`~~ Done (PRs #4 and #5) | Gets the fix to everyone |
| 2 | Add a GitHub Action that runs `uv sync && uv run pytest` on a clean checkout for every PR | Catches "works only on my machine" before merge (root cause 4) |
| 3 | Only promote `staging` to `main` after opening the app from a fresh clone | Root cause 1 |
| 4 | When reporting work, state plainly whether it is committed or pushed, at the start, not as a footnote | Root cause 5 |
