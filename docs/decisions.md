# Decisions

Agreed decisions that affect the whole team. Add new ones at the bottom, and don't delete old ones: mark them **Superseded by #N** instead.

| # | Date | Decision | Why | Who |
|---|------|----------|-----|-----|
| 1 | 2026-11-07 | One worklog file per session in `docs/worklog/` | Avoids merge conflicts on a shared log | sunil |
| 2 | 2026-11-07 | ~~Branch + PR workflow, one approval to merge into `main`~~ **Superseded by #5** | Keeps `main` working; teammate sees every change | sunil |
| 3 | 2026-11-07 | `data/raw/` is read-only; every dataset is logged in `data/sources.csv` | Reproducibility; every figure is traceable to its source, definition and period | sunil |
| 4 | 2026-11-07 | Repo is public, so open published data only | Privacy; no personal or restricted data | sunil |
| 5 | 2026-11-07 | Personal branches `gr`, `hamid`, `sunil` → PR → `staging` → PR + 1 approval → `main`. `main` and `staging` protected | Each person has their own space; `staging` catches conflicts before `main` | sunil |
