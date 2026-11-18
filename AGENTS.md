# AGENTS.md - Tiptree Systems Growth & Post Analytics

This document configures project standards, background context, data schemas, and execution workflows for agents working on the Tiptree Systems social media intelligence MVP.

**Read [docs/implementation-plan.md](docs/implementation-plan.md) before changing collection, metrics, labels or outputs.** It holds the method rules, the decision log and the milestone status. When a milestone ends, update its status table. This file and the plan change together, in the same commit.

---

## 1. Project Overview & Company Context

- **Company:** Tiptree Systems ([tiptreesystems.com](https://tiptreesystems.com))
- **Founder:** Martin Weiss
- **Own X accounts:** `@tiptreesystems` (company) and `@martincsweiss1` (Martin). Both are under 2k followers.
- **Core Products:**
  - **Lacuna:** Dynamic ML research landscape mapping settled vs. contested literature directions.
  - **Althea:** Peer-networked assistant for researchers using privacy-preserving agents and mathematical dispatchers to connect scientists with complementary workflows.
- **Target Audience:** Publishing AI/ML researchers, PhD students, and lab scientists (authenticated via OpenReview / Google Scholar).
- **Current State:** ~1,000 active users, growing ~9% week-over-week.
- **Project Goal:** Build a lean, high-signal data analytics pipeline to evaluate X (Twitter) post mechanics, benchmark adjacent technical developer/research tools, and deliver actionable post templates that drive researcher signups. Signup data is not available, so bookmark rate stands in for it; a posting experiment on the own accounts tests the templates.

---

## 2. Core Operational Principles

1. **Researcher Intent > Vanity Metrics:**
   - Rank posts by bookmark rate (`CR_bmk`) within follower tier. Reach is a minimum bar, never the ranking.
   - Guard against superficial "AI hype" topics (e.g., generic top-10 tool listicles); focus strictly on high-rigor topics (ablations, empirical discrepancies, benchmarks, open literature debates).
2. **Normalized Metrics First:**
   - Raw impressions are biased by author follower count. Compare a post with its author's own trailing-30-day median (`baseline_ratio`), and compare across authors only within a follower tier. Follower-expected reach (`reach_vs_expected`) only describes tiers.
3. **Structured Feature Labeling over Complex Clustering:**
   - Skip raw unsupervised PCA / K-means text clustering for V0.
   - Use deterministic metadata extraction and lightweight LLM-as-a-judge classifiers to label structural hook archetypes, visual media types, and technical depth.
4. **Evidence Before Advice:**
   - A recommendation needs a lift row with at least 20 posts from at least 10 authors, built on labels that met the hand-label agreement targets (plan, Enrichment; or Jev rubric v2 directly under plan decision 60). Thinner cells report "insufficient data".

---

## 3. Data Schema & Analysis Formulas

### Primary Metrics
- **Outperformance Ratio ($R_{\text{out}}$):**
  $$R_{\text{out}} = \frac{\text{Post Impressions}}{\max(\text{Follower Count}, 100)}$$
- **High-Intent Score ($S_{\text{intent}}$):**
  $$S_{\text{intent}} = \frac{3 \times \text{Bookmarks} + 2 \times (\text{Quotes} + \text{Retweets}) + 2 \times \text{Replies} + \text{Likes}}{\max(\text{Impressions}, 1)}$$
- **Bookmark Conversion Rate ($CR_{\text{bmk}}$):** the ranking metric.
  $$CR_{\text{bmk}} = \frac{\text{Bookmarks}}{\max(\text{Impressions}, 1)} \times 1000 \quad (\text{Bookmarks per 1k views})$$
- **Baseline Ratio (`baseline_ratio`):** post impressions divided by the median impressions of the author's eligible posts in the previous 30 days. Needs at least 3 such posts; otherwise empty.
- **Rates across posts:** a lift table cell's rate is pooled (total bookmarks / total impressions × 1000), with intervals from a bootstrap that resamples authors. A single post's rank uses `cr_bmk_shrunk` = (bookmarks + r) / (impressions + 1000) × 1000, where r is the tier's pooled rate.

### Hypothesis-Test Measures
Measures for the hypothesis tests in `notes/40_experiments/` (plan decision 28). "High-Intent Score" in H1 and H2 is `S_intent` above, with replies counted as they are. Ranking stays on `CR_bmk`.
- **Reply rate:** Replies / max(Impressions, 1) × 1000, on posts that are not thread openers. Replies are not collected (plan decision 36), so the author's own replies cannot be subtracted; leaving out thread openers removes most of them.
- **Bookmarks per like:** pooled bookmarks / pooled likes.
- **Quote-to-Retweet ratio:** pooled quotes / reposts (polarization relative to plain amplification, used in H5).
- **Top half (`top_half`):** `cr_bmk_shrunk` above its follower tier's median.

### Analysis Rules
- **Eligible posts:** originals, quote posts and thread openers. Reposts and replies to other people are dropped.
- **Maturity:** a post is scored once it is 7 days old.
- **Per-author cap:** at most 40 eligible posts per author enter the analysis, sampled evenly across the window.
- **Swipe file:** top 5% of mature, filter-passing posts by `cr_bmk_shrunk` within tier, with `baseline_ratio` ≥ 1; hype-flagged and rigor-1 posts excluded; no author above 5%.

### Researcher Post (`is_researcher_post`)
A post written for people who read or write ML research papers: faculty, PhD students, research scientists and engineers, and practitioners sharing training or fine-tuning detail. Product posts aimed at these readers count, including Tiptree's own. Posts written for app developers, AI-tool shoppers, investors or the general public do not. The filter judges the intended reader only; rigor is measured by `technical_rigor_score`. Findings use filter-passing posts only. The one exception is experiment E1 (plan decision 31), which produces no templates.

### Post Categorization Enums
These enums are revised once in milestone 3, from Ben's notes on posts he labels `OTHER` (see the plan; waived for V0 under plan decision 60). Change them through that revision.

- **Hook Archetypes (`hook_archetype`):**
  - `CONTESTED_CLAIM`: Challenges prevailing wisdom or highlights empirical contradiction (e.g., LoRA rank saturation, tokenizer bottlenecks).
  - `LITERATURE_SYNTHESIS`: Mini-survey connecting 3+ disparate papers to reveal a white space.
  - `VISUAL_MAP`: Screenshot or interactive visualization of a research cluster/topology (Lacuna style). Rare outside Tiptree; used for the own accounts and the experiment.
  - `PRODUCT_DEMO`: Direct workflow showcase solving a tedious researcher task.
  - `TECHNICAL_BREAKDOWN`: Paper figure ablation dissection or architecture inspection.
  - `HOT_TAKE_CULTURE`: Perspective on peer review, GPU compute access, or lab dynamics.
  - `OTHER`: None of the above.
- **Visual Asset Types (`visual_type`):**
  - `NONE` (Plain text / thread)
  - `LACUNA_MAP` (Cluster / graph network). Rare outside Tiptree, like `VISUAL_MAP`.
  - `PAPER_FIGURE` (Ablation table, loss curves, architecture diagram)
  - `CODE_TERMINAL` (CLI, code snippet)
  - `VIDEO_DEMO` (Screen recording / UI walkthrough)
  - `OTHER_IMAGE` (Any other image)
- **Technical Rigor (`technical_rigor_score`):**
  - Discrete scale `1` (Hype/introductory) to `5` (Formal math, specific conference benchmarks like NeurIPS/ICLR/SWE-bench, concrete hyperparameter discussion). Anchors for 2–4 are in `src/enrichment/rubric.py`.
- **Framing (`framing`):** `CURIOSITY_GAP`, `OPEN_QUESTION`, `DECLARATIVE_EMPIRICAL`, `DECLARATIVE_OTHER`. Definitions and precedence in [notes/30_concepts/framing.md](notes/30_concepts/framing.md).
- **Poster role (`poster_role`, posts that link a paper):** `ORIGINAL_RESEARCHER`, `CREDENTIALED_RESEARCHER`, `NON_RESEARCHER`. Definitions and precedence in [notes/30_concepts/poster_role.md](notes/30_concepts/poster_role.md).

---

## 4. Accounts & Cohorts

Each post carries a `cohort`:

- **`OWN`:** `@tiptreesystems`, `@martincsweiss1`.
- **`ROSTER`:** researcher accounts admitted by a Jev author check, at most 150 per follower tier, organisations left out (plan decisions 52, 53). Includes the eight hand-picked accounts (the curators `@_akhaliq`, `@rasbt`, `@srush_nlp`, `@karpathy`, `@maximelabonne` and three seeds), flagged `hand_picked` (decision 55). The final handle list is `configs/roster_v1.csv`, written by `src/ingestion/roster.py --finalise --trust-jev` (decision 59; or `--score-review --finalise`) and read by `src/config.py`.
- **`BENCHMARK`:** research-tool organisations, the comparison set for product posts: `@elicitorg`, `@huggingface`, `@arxiv`, `@wandb`.
- **`PANEL`:** posts from accounts outside the roster that link a paper in the paper panel, for same-paper comparisons ([notes/30_concepts/paper_panel.md](notes/30_concepts/paper_panel.md)). Every paper-linked post, in any cohort, carries `paper_id`.

**Follower tiers:** under 2k, 2k–20k, 20k–200k, over 200k. Advice for Tiptree starts from the under-2k tier.

---

## 5. Technology Stack & Data

- **Language & Runtime:** Python 3.11+ (developed on 3.13), managed with `uv`. Secrets (`APIFY_TOKEN`, `JEV_TOKEN`) live in a git-ignored `.env`.
- **Data & Computation:** `pandas`, `pydantic`, `numpy`; `scikit-learn` for experiments E3 and E5; `fastembed` (`BAAI/bge-small-en-v1.5`, `Qdrant/clip-ViT-B-32`) + `umap-learn` + `pillow` for the exploratory 2D post embedding map.
- **Paper metadata:** arXiv and Semantic Scholar APIs (free, rate-limited) for categories, author lists, author h-index and venue.
- **Visualization:** `plotly` for the static overview (`outputs/reports/overview.html`) and exploratory embedding maps (`outputs/reports/embedding_map.html`, `outputs/reports/embedding_impression_map.html`, decision `D9`). The Streamlit dashboard is postponed until after the posting experiment.
- **Collection:** Apify `apidojo/tweet-scraper`. Every query must expect at least 50 posts: combine authors with `OR` or widen the window. Read the plan's Data source section before any collection run.
- **Apify budget:** new spend is capped at $10 from 2026-11-14 (`APIFY_BUDGET_USD`, plan decision 33). `src/ingestion/apify.py` refuses runs that could pass the cap and logs each run to `data/apify_spend.csv`. Raising the cap needs Ben's approval.
- **Classifier:** Jev (`jev-latest`, TypeSafe AI), which reads text and PNG/JPEG images.
- **Storage:** Parquet/CSV in `data/`: `raw/` holds actor output verbatim and is never edited (`raw/_v0/` holds superseded files that ingestion skips); `processed/` holds enriched tables; `swipe_file/` holds the curated posts; `gold/` holds Ben's hand labels.
- **Layout:** the module map is in the plan's Architecture section.

---

## 6. Development Workflow & Commands

### Setup
```bash
uv sync
```

### Run Processing Pipeline
```bash
# Ingest raw data and compute normalized scores
uv run python -m src.ingestion.load_raw --input data/raw/*.jsonl

# Run automated classification / tagging
uv run python -m src.enrichment.classify --model jev-latest

# Compare hand labels with Jev's labels
uv run python -m src.enrichment.evaluate

# Build swipe file, findings report, hypothesis ledger, and static overview page
uv run python -m src.analysis.swipe
uv run python -m src.analysis.report --trust-jev
uv run python -m src.analysis.experiments E1 --data-version v1
uv run python -m src.analysis.charts
uv run python -m src.analysis.embed_map
```

### Tests and Lint
```bash
uv run pytest
uv run ruff check .
```

---

## 7. Guidelines for Agents

- **Keep It Actionable:** Any analysis generated must conclude with concrete writing recommendations for Martin (e.g., "Posts leading with a contested ablation plot achieve $3.2\times$ higher bookmark rates than tool announcements"). Each recommendation cites the lift row it comes from.
- **Never Advise General Consumer Hype Tactics:** Do not recommend clickbait hooks, listicles ("Top 5 AI tools that will replace researchers"), or generic buzzword threads. Maintain academic and technical credibility at all times.
- **Code Quality:** Use typed Python (`pydantic` models for posts, explicit type annotations), vectorized `pandas` operations, and modular utility scripts.

---

## 8. Research Notes

`notes/` is the lab notebook: observations, runs, findings and decisions, recorded as they happen. Read [notes/README.md](notes/README.md) for the entry tags, templates and rules before your first note in a session.

- **Session start:** read `notes/10_project_doc.md` (Current state first), the latest file in `notes/00_daily_log/`, and the file of any experiment you will touch.
- **While working:** append each observation, run, finding, decision, question and blocker to `notes/00_daily_log/YYYY-MM-DD.md` as it happens.
- **Hypothesis tests:** pre-register, run and record them through [notes/40_experiments/README.md](notes/40_experiments/README.md). Every run, null or failed ones included, adds a row to `notes/40_experiments/results.tsv`.
- **Session end:** rewrite the Current state section of `notes/10_project_doc.md` and every hypothesis status, finding, open question or decision the session changed.
