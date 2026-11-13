# Implementation Plan: Tiptree X Post Analytics

Revised 2026-11-12 (revision 3), after a review of the plan against the first full data run.

Changes in revision 3:

- Keyword discovery is replaced by a curated handle list of about 450 researcher accounts and their full timelines. The v0 discovery sample was selected on outcome (see "What the v0 data run showed").
- The researcher filter judges only who a post is written for, not its rigor or register.
- Posts are ranked by bookmark rate, not by reach. Reach is a minimum bar, measured against the author's own median.
- The hand-labelled set is 200 posts, and no lift or recommendation is produced until the agreement targets are met.
- A posting experiment on Tiptree's own accounts is added as milestone 5. The Streamlit dashboard is postponed until after it.
- AGENTS.md is updated in the same change, so the two documents agree.
- `notes/` becomes the research log, and tests E1–E6 for the hypotheses in `notes/10_project_doc.md` are drafted there. The method changes they need are decisions 28–32.

## Milestone status

| # | Milestone | Status |
|---|---|---|
| 0 | Scaffold | Done |
| 1 | Handle list and collection | Not started. The v0 collection (2026-11-11, 2,073 posts) is superseded; collector and adapter code exist. Paper panel (decision 29) not started. |
| 2 | Baselines | Code exists from v0 (maturity, tiers, trailing medians, reach fit). Needs the per-author cap and the new swipe-file bar, then a rerun on new data. |
| 3 | Labels v2 | Rubric v1, Jev judge with images, label cache, label sheet and agreement report exist. The v1 labels on 1,603 v0 posts are unvalidated (0 of 21 sheet rows labelled). Audience rubric, author check, 200-post set, taxonomy revision, `framing` and `poster_role` not started. |
| 4 | Analysis | Not started. `src/analysis/mvp.py` is descriptive only. Hypothesis tests E1–E6 drafted in `notes/40_experiments/` (2026-11-12); each is frozen once milestones 1–3 supply its feasibility counts. |
| 5 | Posting experiment | Not started. Needs milestone 4 and Martin's agreement. |
| 6 | Static overview | `outputs/reports/overview.html` exists on v0 data. Dashboard postponed. |
| 7 | Weekly refresh (optional) | Not started. |

## Decisions

Revision 2 (2026-11-10):

| # | Decision | Answer |
|---|---|---|
| 1 | Classifier | Jev, TypeSafe AI's "System One" model (https://typesafe.ai/blog/introducing-system-one-models-and-jev), model `jev-latest` |
| 2 | Apify actor | `apidojo/tweet-scraper` (https://apify.com/apidojo/tweet-scraper) |
| 3 | Hand-labeller | Ben |
| 4 | Enum additions `OTHER` and `OTHER_IMAGE` | Approved |
| 5 | Signup data | Not available. UTM links on experiment posts are the only bridge to signups. |

Revision 3 (2026-11-12):

| # | Area | Decision |
|---|---|---|
| 6 | Metric | Rank posts by `CR_bmk` within follower tier. Reach is a minimum bar, not the ranking. |
| 7 | Metric | The reach bar is `baseline_ratio` ≥ 1: the post beats its author's trailing-30-day median views. `reach_vs_expected` only describes tiers. |
| 8 | Metric | Lift tables use pooled rates (total bookmarks / total views per cell) with author-clustered bootstrap intervals. Single posts use a rate shrunk toward the tier rate. |
| 9 | Metric | At most 40 eligible posts per author enter the analysis, sampled evenly across the window. All raw posts are kept. |
| 10 | Corpus | Replace keyword discovery with a handle list of about 450 researcher accounts and their full timelines. |
| 11 | Corpus | Handle sources: the 92 authors who pass the v1 filter in v0 data, public X lists of ML researchers, and accounts that post their own arXiv papers. |
| 12 | Corpus | Jev admits a candidate after reading their bio and 5 recent posts. Ben reviews 50 admitted and 25 rejected candidates before collection. |
| 13 | Corpus | Tier quotas: 150 under 2k followers, 150 at 2k–20k, 100 at 20k–200k, 50 over 200k. |
| 14 | Corpus | The five people in AGENTS.md's benchmark list join the handle list. The organisations `@elicitorg`, `@huggingface`, `@arxiv` and `@weights_biases` stay as `BENCHMARK`. `@PapersWithCode` and `@OpenReviewNET` are dropped as dormant. |
| 15 | Collection | Stay on Apify. Monthly windows, several authors per query joined with `OR`, 50–90 expected posts per query; a query that returns 100 is split and rerun. Fallback: the official X API. |
| 16 | Collection | Keep replies (about $28 in total instead of $10), so threads are rebuilt from real self-replies. |
| 17 | Collection | Own and benchmark timelines are collected again with the new method. Old raw files move to `data/raw/_v0/`, unedited. |
| 18 | Labels | The researcher filter judges only the intended reader (definition below). Rigor and register are left to `technical_rigor_score` and `hook_archetype`. |
| 19 | Labels | No lift table or recommendation is produced until the held-out agreement targets are met. |
| 20 | Labels | Hand-labelled set: 200 posts from the new corpus, 50 per tier, labelled blind to Jev, 100 tuning and 100 held out. |
| 21 | Labels | Ben writes a short note on every post he labels `OTHER` in the tuning half. The enums are revised once from those notes before the held-out half is labelled. |
| 22 | Outputs | Findings, lift tables and the swipe file use only posts that pass the audience filter. The full corpus appears only in the coverage table. |
| 23 | Outputs | No fixed template count. A template exists only where a lift row passed the evidence gate. |
| 24 | Outputs | The Streamlit dashboard is postponed until after the experiment; the static overview is extended instead. |
| 25 | Experiment | Martin posts about 3 times a week across both own accounts until 20 posts per arm (about three months). A coin flip assigns each slot. One arm uses Lacuna maps. Every link carries a UTM tag. |
| 26 | Docs | This plan carries a milestone status table updated at the end of each milestone. AGENTS.md is updated in the same change as the plan. |
| 27 | Docs | `notes/` is the research log: a daily log, a project doc kept current, one file per experiment and a run ledger (`notes/40_experiments/results.tsv`). Hypothesis tests are pre-registered and committed before they run on real data. Protocol in `notes/README.md`. |
| 28 | Metric | "High-Intent Score" in H1 and H2 is measured by `CR_bmk` (primary) and `S_intent` (secondary); "technical replies" are not measured. Reply rate, bookmarks per like and `top_half` (AGENTS.md §3) are descriptive measures for the hypothesis tests; ranking stays on `CR_bmk`. Verdicts use 99% intervals and a smallest effect worth acting on of 1.2× (`notes/40_experiments/README.md`). |
| 29 | Corpus | A paper panel: about 300 arXiv papers drawn at random from those that roster posts link, with every post that links them. Posts from accounts outside the roster get cohort `PANEL`; every paper-linked post gets `paper_id`. About 4,500 posts, about $2. Design in `notes/30_concepts/paper_panel.md`. |
| 30 | Labels | Two new labels, each with a Cohen's kappa target of 0.7: `framing` on every post, as a fifth field of the 200-post hand-label set, and `poster_role` (H1's "poster tier") on paper-linked posts, checked on 100 separate paper-linked posts. Definitions in `notes/30_concepts/`. |
| 31 | Outputs | E1 uses paper-linked posts whether or not they pass the researcher filter, because hype explainers write for the general public. This is the one exception to decision 22, and E1 produces no templates. |
| 32 | Stack | scikit-learn joins the dependencies (E3, E5). Paper metadata comes from the arXiv and Semantic Scholar APIs (free, rate-limited). |

## Still open

| # | Item | Needed by |
|---|---|---|
| E | **`OR` joins.** The actor page does not say whether `(from:a OR from:b)` works. The first collection batch checks it; if it fails, the fallback is the official X API ($0.005 per post read, about $350 for 70k posts). | Milestone 1 |
| F | **Older weeks.** In the v0 timelines that hit the 100-post cap, recent weeks are dense and older weeks show about one post a week. The first batch includes older months for `@maximelabonne` and `@_akhaliq`; more posts than v0 had means v0 dropped posts. | Milestone 1 |
| G | **Which X lists.** Ben picks 3–5 public lists of ML researchers. | Milestone 1 |
| H | **Agreement target for the audience filter.** Revision 2 set targets for archetype, visual type and rigor only. Proposed: Cohen's kappa at least 0.8 on `is_researcher_post`. | Milestone 3 |
Resolved: impressions are present (`viewCount`); Jev access and image support (1.13 and later accept PNG/JPEG); Apify paid plan. Items I–M (hypothesis-test measures, paper panel, new labels, E1 scope, new inputs) became decisions 28–32 on 2026-11-12.

## What the v0 data run showed

The first full collection (2026-11-11) loaded 2,073 posts. Three findings shaped this revision:

- **Discovery was selected on outcome.** Six 30-day search slices each stopped at 220 posts (with `maxItems` 500), and each slice's posts were spread across its 30 days. A "Latest" search on terms this common would have returned only the last hours of each slice. The median discovered post had 1,430 likes and 98k views. Only 88 of 1,224 labelled discovered posts passed the researcher filter: "ACL" matched knee injuries and "benchmark" matched markets.
- **Timelines have a per-query cap.** Four timelines stopped at exactly 100 posts (with `maxItems` 300). A one-week test of `@_akhaliq` on 2026-11-12 returned the same 7 posts the six-month pull had for that week, so recent weeks are complete. Older weeks are item F.
- **Tiptree's own accounts are small.** `@tiptreesystems` has 67 followers and `@martincsweiss1` 214. Their 25 eligible posts in six months have a median of 215 views, and 9 have any bookmark.

The one-week test returned 7 posts, which breaks the actor's 50-posts-per-query rule. Verification queries from now on combine authors or months so they expect at least 50 posts.

## Corpus

Four cohorts, tagged in `cohort`:

| Cohort | Source | Purpose |
|---|---|---|
| `OWN` | Timelines of `@tiptreesystems` and `@martincsweiss1` | Scorecard for Tiptree's own posts, and the experiment |
| `ROSTER` | Timelines of about 450 researcher accounts, sampled to tier quotas | What works for researcher posts at every account size (replaces `DISCOVERED`) |
| `BENCHMARK` | Timelines of `@elicitorg`, `@huggingface`, `@arxiv`, `@weights_biases` | Comparison set for product posts from research-tool organisations |
| `PANEL` | Posts from accounts outside the roster that link a paper-panel paper (decision 29) | Same-paper comparisons for hypothesis tests E1, E2, E3 and E5 |

### Definition of a researcher post

> A post written for people who read or write ML research papers: faculty, PhD students, research scientists and research engineers, and practitioners sharing training or fine-tuning detail. Product posts aimed at these readers count, including Tiptree's own. Posts written for app developers, people shopping for AI tools, investors or the general public do not.

The filter judges the intended reader only. A rigorous post and a casual one can both pass; how rigorous a post is gets measured by `technical_rigor_score`, so the filter does not narrow the feature being studied.

### Building the handle list

1. **Candidates.** The 92 authors who passed the v1 filter in v0 data (34 under 2k, 24 at 2k–20k, 26 at 20k–200k, 8 over 200k); members of 3–5 public X lists of ML researchers (item G; the actor accepts List URLs); accounts that post their own arXiv papers, found with phrases such as "our paper" plus `url:arxiv.org`. The v0 authors were found through one viral post, and search skews toward popular posts, so neither source is trusted for cross-author reach; the tier quotas offset the skew.
2. **Admission.** Jev reads each candidate's bio (`author.description`) and 5 recent posts and decides whether they write for ML researchers. Ben reviews 50 admitted and 25 rejected candidates (about 30 minutes) before collection; a high error rate means the admission question is revised and rerun.
3. **Sampling.** Admitted candidates are sampled to the tier quotas: 150 under 2k, 150 at 2k–20k, 100 at 20k–200k, 50 over 200k. The five people from AGENTS.md's benchmark list are included in their tiers.

## Data source: Apify `apidojo/tweet-scraper`

What the actor page states:

- **Price:** $0.40 per 1,000 posts.
- **Input:** X advanced-search queries, handle lists, Tweet/Profile/Search/List URLs, `sort` of `Latest` or `Top`, `maxItems`.
- **Output:** `id`, `url`, `text`, `createdAt`, `viewCount`, `likeCount`, `retweetCount`, `replyCount`, `quoteCount`, `bookmarkCount`, `isReply`, `isQuote`, media; author `userName`, `followers`, `description`, `statusesCount`.
- **Rules:** every query must return at least 50 posts; one concurrent run with up to 5 queries; no repeated queries at short intervals; no single-post or conversation scraping; `customMapFunction` must not filter.

### Collection design

- One query covers one calendar month and joins several authors: `(from:a OR from:b ...) since:YYYY-MM-01 until:YYYY-MM-01 -filter:retweets`. Group sizes come from each author's posting rate in the candidate data and target 50–90 posts per query, between the actor's minimum and the observed 100-post cap.
- A query that returns exactly 100 posts is split into two half-month queries and rerun.
- Replies are kept. Threads are rebuilt from an author's own replies; `thread_length` falls back to a text heuristic only where that fails.
- Window: 180 days. Estimated volume: 450 authors × 26 weeks × about 6 posts a week ≈ 70k posts ≈ $28. About 340 queries in about 70 runs.
- Paper panel: `url:` queries for about 300 arXiv IDs, grouped so each expects at least 50 posts; about 4,500 posts, about $2. A first batch of 30 papers checks that `url:` matches arXiv IDs and counts posters per paper. Design in `notes/30_concepts/paper_panel.md`.
- The first batch is the test for items E and F.

Risks specific to this route:

- **Terms of service.** X's terms prohibit scraping without consent. The official API returns the same public fields and stays available as a drop-in adapter.
- **Actors break or change output without notice.** Raw output is stored verbatim and the adapter maps field aliases, so a switch of actor only touches one module.
- **No own-post click metrics.** URL and profile clicks exist only through the official API with account sign-in, and only for posts under 30 days old.

## Architecture

Data moves one way. Raw files are stored verbatim and never edited; everything downstream can be rebuilt from them. Superseded raw files move to `data/raw/_v0/`, which ingestion does not read.

```text
candidate sources ─► roster.py (Jev admission, quotas) ─► config handle list
                                                               │
Apify actor runs ─► data/raw/ ─► adapters ─► posts.parquet + account_snapshots.parquet
                                                 │
                       ┌─────────────────────────┼────────────────────────┐
                metrics + baselines        rule features          jev classifier (cached)
                       └─────────────────────────┼────────────────────────┘
                                       posts_enriched.parquet
                                                 │
                       lift tables ── swipe file ── findings + templates ── static overview
```

```text
src/
  schema.py        # Post, AccountSnapshot, PostLabels, enums: the single contract
  config.py        # handles, cohorts, tier quotas, window, thresholds
  ingestion/
    roster.py      # candidate pool, Jev author admission, review sheet, quota sampling
    apify.py       # the only module that talks to Apify; writes raw JSONL
    collect.py     # monthly OR-batched timeline queries, split on cap
    panel.py       # paper panel: seed IDs, url: queries, arXiv and Semantic Scholar metadata
    adapters.py    # raw actor JSON or export CSV -> Post, accepting field-name aliases
    load_raw.py    # CLI from AGENTS.md: validate, dedupe, write Parquet, add metrics
  metrics/
    formulas.py    # the AGENTS.md formulas as pure vectorised functions
    baselines.py   # maturity, trailing author medians, per-author cap, shrunk CR_bmk, reach fit
  enrichment/
    rules.py       # deterministic features and the hype lint
    rubric.py      # audience definition, archetype and rigor anchors
    judge.py       # provider-neutral Judge interface, Jev implementation
    classify.py    # CLI from AGENTS.md: --model, resumable, cached by label version
    label_sheet.py # stratified, blind hand-label sheet
    evaluate.py    # hand labels vs judge: agreement report
  analysis/
    lift.py        # pooled lifts, author-clustered bootstrap, evidence gate
    swipe.py       # swipe-file selection -> data/swipe_file/
    report.py      # findings and templates, generated from the lift tables
    experiments.py # E1–E6 entry points: stratified rate ratio, negative control, summary block
    charts.py      # static overview page
tests/  scripts/  configs/  notes/  outputs/reports/  docs/  data/{raw,processed,swipe_file,gold}/
```

Setup uses `uv` on Python 3.13 (`requires-python >= 3.11`). Secrets live in a git-ignored `.env`.

### Posts table

| Group | Columns |
|---|---|
| Identity | `post_id`, `author_handle`, `author_id`, `cohort`, `url`, `created_at`, `collected_at`, `source`, `paper_id` (arXiv ID, when the post links a paper) |
| Author | `followers_at_collection` (required), `follower_tier` |
| Content | `text`, `post_kind` (original, quote, thread opener), `thread_length`, `media`, `link_kinds` |
| Counts | `impressions`, `likes`, `replies`, `reposts`, `quotes`, `bookmarks` |
| Metrics | `r_out`, `s_intent`, `cr_bmk`, `cr_bmk_shrunk`, `baseline_ratio`, `reach_vs_expected`, `pctile_in_tier`, `in_author_cap` |
| Rule features | `has_media`, `media_kind`, `has_link`, `char_len`, `has_number`, `mentions_venue`, `has_arxiv_id`, `hype_flags`, `posted_hour_utc` |
| Labels | `is_researcher_post`, `hook_archetype`, `visual_type`, `technical_rigor_score`, `framing`, `poster_role`, `label_confidence`, `label_rationale`, `label_version` |

Side tables: `account_snapshots` (follower counts appended on every run), `labels` (classifier cache keyed by post and label version) and `roster` (candidate, source, admission decision, review label, tier).

A post without `followers_at_collection` is rejected at ingestion.

## Metrics and method

The three AGENTS.md formulas are implemented exactly, including the `max(followers, 100)` and `max(impressions, 1)` floors.

- **Ranking metric: `CR_bmk`**, compared within follower tier. Bookmarks are the clearest signal that a researcher wants to come back to a post.
- **Reach bar: `baseline_ratio`** = post views / the author's trailing-30-day median views over eligible posts. A post needs `baseline_ratio` ≥ 1 to enter the swipe file. Posts whose author has fewer than 3 eligible posts in the previous 30 days have no baseline; they stay out of the swipe file but count in lift tables.
- **Pooled rates for lifts.** A cell's bookmark rate is total bookmarks / total views × 1000, with a 95% interval from a bootstrap that resamples authors, not posts.
- **Shrunk rates for single posts.** `cr_bmk_shrunk` = (bookmarks + r) / (views + 1000) × 1000, where r is the tier's pooled bookmarks per 1k views. This treats each post as if it had 1,000 extra views at its tier's pooled rate. One bookmark on a 200-view post no longer outranks a large account's typical post.
- **Per-author cap.** At most 40 eligible posts per author enter the analysis, sampled evenly across the window (`in_author_cap`), so prolific authors do not dominate pooled rates.
- **`reach_vs_expected`** (log views on log followers) is refit on `ROSTER` posts and used only to describe tiers.
- **Follower tiers:** under 2k, 2k–20k, 20k–200k, over 200k. Advice for Tiptree comes from the under-2k tier first.
- **Eligible posts:** originals, quote posts and thread openers. Reposts and replies to other people are dropped.
- **Maturity:** a post is scored once it is 7 days old.
- **Follower counts are as of collection.** Each run appends a snapshot.
- **Minimum evidence:** a lift is reported only for at least 20 posts from at least 10 distinct authors (3 for within-author comparisons). Thinner cells show "insufficient data" and cannot produce a recommendation.

## Enrichment

- **Rules:** media kind, link type, length, numeric claims, venue and benchmark mentions, arXiv IDs, thread length, posting time, and a hype flag for listicle and clickbait patterns that doubles as a lint on generated text.
- **Classifier (Jev):** one call per post returns `is_researcher_post` (audience definition above), `hook_archetype`, `visual_type` for photos (Jev reads PNG/JPEG) and `technical_rigor_score`, each with its probability. Video is classified by rule. A second Jev question, on bio and 5 recent posts, admits authors to the handle list. The same per-post call also returns `framing`, and `poster_role` for posts that link a paper; `PAPER_AUTHOR` also comes from matching the display name against the arXiv author list (decision 30).
- **Rubric v2:** the audience-only definition, anchors for rigor scores 2–4, precedence rules for overlapping archetypes. A rubric change bumps `label_version` and relabels everything (cents).
- **Taxonomy revision.** In the v1 labels on 175 passing v0 posts, `OTHER` was 51% of archetypes and `OTHER_IMAGE` 41% of visual types; `LITERATURE_SYNTHESIS` had 0 posts and `VISUAL_MAP` 5. The most common researcher post, a paper announcement, had no archetype. Ben notes what each `OTHER` post in the tuning half is, and the enums are revised once from those notes before the held-out half (likely `PAPER_ANNOUNCEMENT`, `RESOURCE_SHARE` and a split of `OTHER_IMAGE`). `VISUAL_MAP` and `LACUNA_MAP` are kept for Tiptree's own posts; they will not reach the evidence gate in the corpus.
- **Validation:** 200 posts from the new corpus, 50 per tier, labelled by Ben on all four fields without seeing Jev's labels; 100 tuning and 100 held out. Targets on the held-out half: Cohen's kappa at least 0.7 for archetype and 0.8 for visual type, rigor within one point on 85% of posts, and the audience-filter target in item H. Classes with fewer than 10 held-out examples are reported but not held to the targets. `framing` is a fifth field on the same set. `poster_role` is checked on 100 separate paper-linked posts (25 per Jev role) plus 50 author-name matches. Both have a target of Cohen's kappa at least 0.7.
- **Gate:** no lift table, template or recommendation is produced from labels that have not met the targets.
- **Mechanics:** labels cached by post and `label_version` (hash of rubric and model). Failures recorded as unlabelled with a reason.

## Outputs

- **Swipe file:** top 5% of mature, filter-passing posts by `cr_bmk_shrunk` within follower tier, with `baseline_ratio` ≥ 1. Hype-flagged and rigor-1 posts are excluded, no author supplies more than 5%, and `curation.csv` lets a person drop entries.
- **Findings report (`outputs/reports/findings.md`):** a coverage table over the full corpus, then findings on filter-passing posts only, each with interval and sample size; Tiptree's two accounts placed on the under-2k distribution; recommendations for Martin, each generated from a lift row that passed the evidence gate. No inline lists of author handles.
- **Post templates:** one per lift row that passed the evidence gate, with no target count. Each has a hook pattern, evidence slot, visual spec, call-to-action placement, measured lift and three linked examples, and passes the hype lint. Ideas that did not pass may enter the experiment, labelled untested.
- **Static overview:** `outputs/reports/overview.html` extended with tier views, the archetype by visual-type lift heatmap, the swipe file and the Tiptree scorecard. A Streamlit dashboard is reconsidered after the experiment.

## Posting experiment

Correlations in the corpus suggest templates; only Tiptree posting them shows whether they work for Tiptree.

- **Accounts:** `@tiptreesystems` and `@martincsweiss1`, about 3 posts a week between them.
- **Arms:** template posts from milestone 4 against Martin's usual posts. One arm uses Lacuna maps, since the corpus has too few map posts to benchmark them.
- **Assignment:** a coin flip decides which posting slot gets a template, so topic and time of day do not line up with the arm.
- **Stopping rule:** 20 posts per arm, about three months, not a fixed date.
- **Measures:** pooled `CR_bmk` per arm and `baseline_ratio` against the account's own median. Every link carries a UTM tag (`utm_source=x`, `utm_campaign=<arm>`) so signups can be attributed if web analytics becomes available.
- **Expectation:** at these view counts only large differences will show. A null result is reported as "no large effect", not "no effect".
- **Needs:** Martin's agreement to the cadence.

## Hypothesis tests

The hypotheses (H1–H4) and open questions live in `notes/10_project_doc.md`. Their tests, E1–E6, are in `notes/40_experiments/`, which also holds the estimator (stratified rate ratio), evidence gate, verdict rule and run ledger. They run in milestone 4 on milestone 1–3 outputs, plus the paper panel (decision 29) and two new labels (decision 30). Levers that E2 and E4 support become the template arm of the posting experiment, the only causal test.

## Milestones

| # | Milestone | Needs | Done when |
|---|---|---|---|
| 0 | Scaffold | Nothing | Done |
| 1 | Handle list and collection: candidate pool, Jev admission, Ben's review of 75 candidates, quota sampling, monthly `OR`-batched collection of `ROSTER`, `OWN` and `BENCHMARK`, then the paper panel (first batch of 30 papers, then the rest), v0 raw files moved to `data/raw/_v0/` | Items E, F, G | Admission review passed; coverage table per cohort and tier meets the quotas; first-batch checks for E, F and the panel recorded here; 10 posts spot-checked against X |
| 2 | Baselines: trailing author medians, per-author cap, shrunk `CR_bmk`, reach fit | Milestone 1 | Sanity table per tier reviewed; MVP and sanity reports regenerated on new data without stale text |
| 3 | Labels v2: audience rubric, 200-post hand-labelled set (with `framing`), 100 paper-linked posts for `poster_role`, taxonomy revision, relabel, agreement report | Milestone 1, item H | Held-out targets met and the corpus labelled |
| 4 | Analysis: lift tables, swipe file, findings, templates, hypothesis tests E1–E6 | Milestones 2–3 | Every number in the findings traces to a lift row or a ledger row |
| 5 | Posting experiment | Milestone 4, Martin's agreement | 20 posts per arm; result written up |
| 6 | Static overview extended; dashboard reconsidered | Milestone 4 | Overview runs on real data and matches the report |
| 7 | Weekly refresh (optional) | Milestone 6 | A refresh adds a week without re-collecting old posts |

## Risks

- **Association, not cause.** Lifts are correlations. The experiment is the real test, and it can only detect large effects.
- **Handle-list bias.** Public lists favour visible accounts and the v0 seeds were found through a viral post. Tier quotas limit this; the sources and admission counts are reported in the findings.
- **Unvalidated labels.** Until milestone 3, every archetype, rigor and filter label is Jev's alone.
- **Scraping route** risks are listed under Data source.

## Out of scope for V0

Unsupervised clustering, judging reply quality (replies are counted, not read), automated posting, the Streamlit dashboard (until after the experiment), and platforms other than X.
