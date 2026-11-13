# Tiptree Systems: growth and post analytics

X post-mechanics analysis for researcher signups. Method, decisions and milestone status: [docs/implementation-plan.md](docs/implementation-plan.md). Agent conventions: [AGENTS.md](AGENTS.md).

## Setup
```bash
uv sync
cp .env.example .env   # add APIFY_TOKEN, JEV_TOKEN
```

## Directory map
| Path | Contents |
|---|---|
| `src/` | Reusable code: ingestion, metrics, enrichment, analysis |
| `configs/` | Experiment and pipeline configs (handles and quotas currently in `src/config.py`) |
| `scripts/`, `scripts/scratch/` | Entrypoints; exploratory notebooks and throwaway prototypes |
| `data/{raw,processed,swipe_file,gold}/` | Datasets (gitignored); `raw/` is never edited |
| `outputs/` | Generated artifacts (gitignored); `outputs/reports/` is tracked |
| `notes/` | Research log ([protocol](notes/README.md)): `00_daily_log/`, `10_project_doc.md`, `20_literature/`, `30_concepts/`, `40_experiments/` (experiments and run ledger) |
| `docs/` | Implementation plan |
| `tests/` | pytest suite and fixtures |
