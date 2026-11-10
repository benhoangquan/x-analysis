# CLAUDE.md - Tiptree Systems Growth & Post Analytics

This document configures project standards, background context, data schemas, and execution workflows for Claude Code working on the Tiptree Systems social media intelligence MVP.

---

## 1. Project Overview & Company Context

- **Company:** Tiptree Systems ([tiptreesystems.com](https://tiptreesystems.com))
- **Founder:** Martin Weiss
- **Core Products:**
  - **Lacuna:** Dynamic ML research landscape mapping settled vs. contested literature directions.
  - **Althea:** Peer-networked assistant for researchers using privacy-preserving agents and mathematical dispatchers to connect scientists with complementary workflows.
- **Target Audience:** Publishing AI/ML researchers, PhD students, and lab scientists (authenticated via OpenReview / Google Scholar).
- **Current State:** ~1,000 active users, growing ~9% week-over-week.
- **Project Goal:** Build a lean, high-signal data analytics pipeline to evaluate X (Twitter) post mechanics, benchmark adjacent technical developer/research tools, and deliver actionable post templates that drive researcher signups.

---

## 2. Core Operational Principles

1. **Researcher Intent > Vanity Metrics:**
   - Optimize for high-intent signals (Bookmarks, Retweets/Quotes, In-depth Replies) over passive vanity views or generic likes.
   - Guard against superficial "AI hype" topics (e.g., generic top-10 tool listicles); focus strictly on high-rigor topics (ablations, empirical discrepancies, benchmarks, open literature debates).
2. **Normalized Metrics First:**
   - Raw impressions are biased by author follower count. Normalize all engagement by author follower count or 30-day baseline median.
3. **Structured Feature Labeling over Complex Clustering:**
   - Skip raw unsupervised PCA / K-means text clustering for V0.
   - Use deterministic metadata extraction and lightweight LLM-as-a-judge classifiers to label structural hook archetypes, visual media types, and technical depth.

---

## 3. Data Schema & Analysis Formulas

### Primary Metrics
- **Outperformance Ratio ($R_{\text{out}}$):**
  $$R_{\text{out}} = \frac{\text{Post Impressions}}{\max(\text{Follower Count}, 100)}$$
- **High-Intent Score ($S_{\text{intent}}$):**
  $$S_{\text{intent}} = \frac{3 \times \text{Bookmarks} + 2 \times (\text{Quotes} + \text{Retweets}) + 2 \times \text{Replies} + \text{Likes}}{\max(\text{Impressions}, 1)}$$
- **Bookmark Conversion Rate ($CR_{\text{bmk}}$):**
  $$CR_{\text{bmk}} = \frac{\text{Bookmarks}}{\max(\text{Impressions}, 1)} \times 1000 \quad (\text{Bookmarks per 1k views})$$

### Post Categorization Enums
- **Hook Archetypes (`hook_archetype`):**
  - `CONTESTED_CLAIM`: Challenges prevailing wisdom or highlights empirical contradiction (e.g., LoRA rank saturation, tokenizer bottlenecks).
  - `LITERATURE_SYNTHESIS`: Mini-survey connecting 3+ disparate papers to reveal a white space.
  - `VISUAL_MAP`: Screenshot or interactive visualization of a research cluster/topology (Lacuna style).
  - `PRODUCT_DEMO`: Direct workflow showcase solving a tedious researcher task.
  - `TECHNICAL_BREAKDOWN`: Paper figure ablation dissection or architecture inspection.
  - `HOT_TAKE_CULTURE`: Perspective on peer review, GPU compute access, or lab dynamics.
- **Visual Asset Types (`visual_type`):**
  - `NONE` (Plain text / thread)
  - `LACUNA_MAP` (Cluster / graph network)
  - `PAPER_FIGURE` (Ablation table, loss curves, architecture diagram)
  - `CODE_TERMINAL` (CLI, code snippet)
  - `VIDEO_DEMO` (Screen recording / UI walkthrough)
- **Technical Rigor (`technical_rigor_score`):**
  - Discrete scale `1` (Hype/introductory) to `5` (Formal math, specific conference benchmarks like NeurIPS/ICLR/SWE-bench, concrete hyperparameter discussion).

---

## 4. Benchmark Accounts

When collecting comparison data, prioritize these handles:
- **Tools & Platforms:** `@elicitorg`, `@weights_biases`, `@huggingface`, `@arxiv`, `@PapersWithCode`, `@OpenReviewNET`
- **High-Signal Technical Curators:** `@_akhaliq`, `@rasbt`, `@srush_nlp`, `@karpathy`, `@maximelabonne`

---

## 5. Technology Stack & Directory Structure

- **Language & Runtime:** Python 3.11+
- **Data & Computation:** `pandas`, `pydantic`, `numpy`
- **Visualization & UI:** `streamlit`, `plotly`, `altair`
- **Storage:** Clean local Parquet/CSV in `data/`

### Suggested Project Layout
```text
.
├── CLAUDE.md
├── pyproject.toml / requirements.txt
├── data/
│   ├── raw/                # Scraped or exported CSV/JSON files
│   ├── processed/          # Enriched data with features and intent scores
│   └── swipe_file/         # Curated top 5% outperforming posts
├── src/
│   ├── ingestion/          # Parsers for X export CSVs or API responses
│   ├── enrichment/         # Rule-based tags and LLM-judge classifier
│   ├── metrics/            # Formula calculations (Outperformance, Intent)
│   └── dashboard.py        # Streamlit presentation interface
└── notebooks/              # Exploratory data analysis notebooks
```

---

## 6. Development Workflow & Commands

### Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run Processing Pipeline
```bash
# Ingest raw data and compute normalized scores
python -m src.ingestion.load_raw --input data/raw/posts_export.csv

# Run automated classification / tagging
python -m src.enrichment.classify --model gpt-4o-mini # or local/Claude API
```

### Run Dashboard
```bash
streamlit run src/dashboard.py
```

---

## 7. Guidelines for Claude Code

- **Keep It Actionable:** Any analysis generated must conclude with concrete writing recommendations for Martin (e.g., "Posts leading with a contested ablation plot achieve $3.2\times$ higher bookmark rates than tool announcements").
- **Never Advise General Consumer Hype Tactics:** Do not recommend clickbait hooks, listicles ("Top 5 AI tools that will replace researchers"), or generic buzzword threads. Maintain academic and technical credibility at all times.
- **Code Quality:** Use typed Python (`pydantic` models for posts, explicit type annotations), vectorized `pandas` operations, and modular utility scripts.