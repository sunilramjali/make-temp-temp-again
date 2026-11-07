# CLAUDE.md

Research project on temporary accommodation (TA) for families in London, with a Newham case study. Three people (GR, Hamid, Sunil) work on it, each in their own Claude Code sessions. See README.md for the full guide and methodology.

## At the start of every session

1. Run `git pull` (or remind the user to), then `git status` and `git branch`.
2. Read the 3 most recent files in `docs/worklog/` (by filename date) and `docs/decisions.md`.
3. Give the user a short catch-up: what was done last, by whom, open questions, and suggested next steps.
4. Don't re-open decisions recorded in `docs/decisions.md` unless the user asks to.

## At the end of a session (or when the user asks)

Write `docs/worklog/YYYY-MM-DD_<name>.md` using `docs/worklog/_TEMPLATE.md`. Ask whose session it is if that isn't clear. Add any new decisions to `docs/decisions.md` and any new data gaps to `docs/evidence_gaps.md`.

## Rules

- Never modify files in `data/raw/`. Cleaning goes in `src/ta_london/` or notebooks.
- Every new dataset gets a row in `data/sources.csv` (source, definition, reference period).
- In `policy/services_map.csv`, keep what is *offered* separate from evidence of *uptake* or *outcomes*.
- Findings are descriptive. Never word a comparison as causal.
- The repo is public: no personal data and nothing identifying individual families.
- The Streamlit app in `app/` only displays results. Keep cleaning and indicator logic in `src/`.
- Team: GR, Hamid, Sunil. Each works on their personal branch (`gr`, `hamid`, `sunil`), which is merged via PR into `staging`, then `staging` into `main` (both protected). Never commit to `staging` or `main` directly. At session start, check the current branch matches the user, and suggest `git merge origin/staging`. Commit or push only when the user asks.
