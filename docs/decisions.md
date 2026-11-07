# Decisions

Agreed decisions that affect the whole team. Add new ones at the bottom, and don't delete old ones: mark them **Superseded by #N** instead.

| # | Date | Decision | Why | Who |
|---|------|----------|-----|-----|
| 1 | 2026-11-07 | One worklog file per session in `docs/worklog/` | Avoids merge conflicts on a shared log | sunil |
| 2 | 2026-11-07 | ~~Branch + PR workflow, one approval to merge into `main`~~ **Superseded by #5** | Keeps `main` working; teammate sees every change | sunil |
| 3 | 2026-11-07 | `data/raw/` is read-only; every dataset is logged in `data/sources.csv` | Reproducibility; every figure is traceable to its source, definition and period | sunil |
| 4 | 2026-11-07 | Repo is public, so open published data only | Privacy; no personal or restricted data | sunil |
| 5 | 2026-11-07 | Personal branches `gr`, `hamid`, `sunil` → PR → `staging` → PR + 1 approval → `main`. `main` and `staging` protected | Each person has their own space; `staging` catches conflicts before `main` | sunil |
| 6 | 2026-11-07 | Stack: Python 3.12 + uv, pandas/pyarrow, pandera (tidy schema), plotly, geopandas, Streamlit, ruff, pytest. Datasets go untouched in `data/raw/`, loaders in `src/ta_london/`, app is display-only. GR's policies are markdown files in `policy/`, shown on the Policies page | Fixes the open stack question from the first worklog; keeps one traceable route from raw file to chart | sunil |
| 7 | 2026-11-07 | Pipeline conventions: (a) shares and ratios are calculated in `src/ta_london/indicators.py`, never in the app; (b) a share is NaN if any part of its group is suppressed or missing; (c) TA7 zero-day averages are treated as missing; (d) ethnicity shares are shown both of all households and of known only, with the not-known share always visible; (e) waiting-list series starts 2012 (the Local Authority Housing Statistics era); (f) values MHCLG imputed are flagged `estimated` | Keeps one traceable route from raw file to chart, and avoids showing partial or misleading percentages | sunil |
