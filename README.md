# Temporary Accommodation in London: Newham Case Study

Research into families in temporary accommodation (TA) across London, with Newham examined in detail, to find the barriers to moving on and test whether a coordinated move-on pathway would fill a genuine gap.

> **New here?** Read [Quick start](#quick-start), then [Starting a work session](#starting-a-work-session). It takes about 5 minutes.

---

## Contents

1. [Project overview](#project-overview)
2. [Quick start](#quick-start)
3. [Project structure](#project-structure)
4. [Starting a work session](#starting-a-work-session)
5. [Ending a work session](#ending-a-work-session)
6. [Git workflow](#git-workflow)
7. [Data rules](#data-rules)
8. [Methodology](#methodology)

---

## Project overview

TA is meant to be short-term housing, but families can stay in it for a long time while they wait for suitable settled housing. This project looks at:

- who is affected
- how accommodation type and length of stay vary
- what support and move-on routes councils offer
- how social housing supply and private rents limit the options available

**Focus:** households with dependent children and pregnant women. We compare London boroughs using consistent indicators where possible, then examine Newham in detail.

**Working concept (to be tested, not assumed):** a *coordinated move-on pathway*. Each family gets one plan with a named contact, a clear explanation of the routes (social housing, private rented sector), practical help with applications and deposits, and regular updates while they wait. The research decides whether to refine or reject it.

---

## Quick start

```bash
git clone https://github.com/sunilramjali/make-temp-temp-again.git
cd make-temp-temp-again
```

**Environment:** the tech stack is still being finalised (planned: Python 3.12 + uv, pandas, Plotly, Streamlit). See [`docs/decisions.md`](docs/decisions.md). Once `pyproject.toml` is added:

```bash
uv sync                         # install dependencies
uv run jupyter lab              # notebooks
uv run streamlit run app/Home.py   # dashboard
```

---

## Project structure

```
data/
  raw/            Original downloads. NEVER edit, only add.
  interim/        Partially cleaned / reshaped data
  processed/      Analysis-ready tables used by notebooks and the app
  reference/      Lookups: borough codes, LHA rates, population denominators
  sources.csv     Register: one row per dataset (source, definition, period)
policy/
  national/       Legislation, Code of Guidance, national policy
  newham/         Newham strategies, allocations scheme, budget reports
  comparators/    Comparator boroughs' equivalent documents
  services_map.csv  What each borough offers vs evidence it is used or works
notebooks/        Analysis, numbered by methodology step (01_…, 02_…)
src/ta_london/    Reusable Python code: loading, cleaning, indicators
app/              Streamlit dashboard (displays results only, no cleaning logic)
docs/
  worklog/        Session log: one file per work session
  decisions.md    Decisions we've agreed, and why
  evidence_gaps.md  Questions the data cannot answer
outputs/          Generated figures and tables (not committed)
CLAUDE.md         Context file read automatically by Claude Code
```

---

## Starting a work session

Before you start any work, spend 3 minutes catching up so we don't duplicate or contradict each other:

1. **Update:** `git checkout <yourname> && git pull && git merge origin/staging`
2. **Read the latest worklog entries** in [`docs/worklog/`](docs/worklog/). Files sort by date, so check the last 2–3, especially the **Next steps** and **Open questions** sections.
3. **Skim [`docs/decisions.md`](docs/decisions.md)** for anything added since your last session.
4. **Check GitHub Issues** to see what's assigned to you or unclaimed.
5. **Work on your own branch** (`gr`, `hamid` or `sunil`), never on `staging` or `main` (see [Git workflow](#git-workflow)).

**Using Claude Code?** It reads `CLAUDE.md` automatically, and that file tells it to read the latest worklog entries first. You can also say: *"Catch me up from the worklog."*

## Ending a work session

1. **Write a worklog entry:** copy [`docs/worklog/_TEMPLATE.md`](docs/worklog/_TEMPLATE.md) to `docs/worklog/YYYY-MM-DD_yourname.md`, e.g. `2026-11-08_hamid.md` (add `_2` for a second session that day).
2. If you made a decision that affects others, add it to `docs/decisions.md`.
3. If you found something the data can't answer, add it to `docs/evidence_gaps.md`.
4. Commit and push to your branch. If the work is ready, open a PR → `staging`.

**Team:** GR · Hamid · Sunil

Claude Code users can say: *"Write my worklog entry for this session."*

**Why one file per session?** Two people editing one shared log file causes merge conflicts. Separate dated files never conflict and still read as a timeline.

---

## Git workflow

```
gr ──────┐
hamid ───┼──PR──▶ staging ──PR (reviewed)──▶ main
sunil ───┘
```

| Branch | Purpose | Protection |
|---|---|---|
| `main` | Stable, reviewed work only | Protected: PR from `staging` + 1 approval; no direct pushes |
| `staging` | Everyone's work combined and checked together | Protected: PR required; no direct pushes |
| `gr`, `hamid`, `sunil` | Your personal working branch | Push freely |

**Daily routine:**

```bash
git checkout <yourname>          # e.g. git checkout hamid
git pull                         # get your branch's latest
git merge origin/staging         # bring in teammates' merged work (do this often!)
# ... work, commit small and often ...
git push
```

- When a piece of work is ready, open a **Pull Request from your branch → `staging`**.
- When `staging` is in a good state, open a **PR `staging` → `main`**, which a teammate reviews and approves.
- Commit messages should say what changed: `Add MHCLG TA table ingest for 2019–2024`
- Use **GitHub Issues** for tasks. Assign yourself before starting, to avoid duplicating work.
- Merge `staging` into your branch often. The longer branches drift apart, the harder the merge conflicts get.

---

## Data rules

1. **Official sources first** (MHCLG/DLUHC homelessness statistics, ONS, VOA, council reports).
2. **Never edit `data/raw/`.** All cleaning happens in code (`src/` or notebooks), so it can be reproduced.
3. **Every dataset gets a row in `data/sources.csv`**: source, URL, definition, reference period, date accessed.
4. **The repo is public:** only open, published data. No personal data, no data from FOI responses with restrictions, and nothing identifying individual families.
5. **Large files (>50 MB)** are not committed. Record the download link in `sources.csv` instead.
6. **Descriptive, not causal.** Comparisons show patterns but cannot prove that one factor caused another. Word findings accordingly.
7. **Use rates only with a comparable denominator** (e.g. households per 1,000 from the same year's estimates).

---

## Methodology

| # | Step | Where |
|---|------|-------|
| 1 | **London comparison:** borough TA household numbers and trends from official statistics. Rates only where a comparable denominator exists | `data/`, `notebooks/01_*` |
| 2 | **Newham profile:** households with children, composition, accommodation type, length of stay, out-of-borough placements. Record where pregnant households aren't separately identified | `notebooks/02_*` |
| 3 | **Support & move-on routes:** Newham and comparator services (prevention, PRS access, landlord incentives, deposits, allocations, tenancy support). What is offered is recorded separately from uptake and outcomes | `policy/` |
| 4 | **Affordability:** social lettings and waiting lists vs private rents and LHA, with matching periods and bedroom sizes | `notebooks/04_*` |
| 5 | **Spending:** TA budgets, outturn, forecasts from council reports. Supplier payments are supporting evidence only | `policy/`, `notebooks/05_*` |
| 6 | **Synthesis:** recurring barriers, provision gaps, unanswerable questions. Refine or reject the pathway concept | `docs/` |
