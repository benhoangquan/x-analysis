# Implementation Plan: Tiptree X Post Analytics

Status: plan only, nothing built. Revised 2026-11-10 (revision 2).

Changes in revision 2:

- Data source is Apify instead of the official X API.
- Classifier is "jev" (identity still to be confirmed, see open questions).
- Own accounts are `@tiptreesystems` and `@martincsweiss1`.
- The corpus is researcher posts from across X, not only the benchmark handles in AGENTS.md. Author follower count is a required field on every post.

## Decisions (answered 2026-11-10)

| # | Decision | Answer |
|---|---|---|
| 1 | Classifier | Jev, TypeSafe AI's "System One" model (https://typesafe.ai/blog/introducing-system-one-models-and-jev) |
| 2 | Apify actor | `apidojo/tweet-scraper` (https://apify.com/apidojo/tweet-scraper) |
| 3 | Researcher post definition | See Corpus |
| 4 | Hand-labeller | Ben |
| 5 | Enum additions `OTHER` and `OTHER_IMAGE` | Approved |
| 6 | Signup data | Not available; the signup join is dropped from milestone 6 |

## Still open

| # | Item | Needed by |
|---|---|---|
| A | **Impressions from the actor.** The actor page's sample output shows likes, reposts, replies, quotes, bookmarks and author followers, but no view count. Without views, none of the three AGENTS.md formulas can be computed. The 50-post test run settles this; if views are absent, another actor or the official X API is needed. | Milestone 1 |
| B | ~~**Jev access.**~~ Resolved 2026-11-10: token in `.env` (`JEV_TOKEN`), endpoint `POST https://api.typesafe.ai/v1/systemone`, model `jev-latest` (1.14). Jev is in early access behind a waitlist. The blog post gives no model ID, API URL or authentication; those are in the docs (https://docs.typesafe.ai/introduction) and console (https://console.typesafe.ai/). Access and an API key are needed. | Milestone 3 |
| C | ~~**Jev does not accept images.**~~ Resolved: Jev 1.13 and 1.14 accept PNG/JPEG (not video). `visual_type` for photos comes from Jev; video is rule-based. The original note: The post says it does not run on images yet. `visual_type` therefore needs a different path (see Enrichment). | Milestone 3 |
| D | Apify token on a paid plan (free accounts cannot call this actor through the API). | Milestone 1 |

## Corpus

Three cohorts, tagged in `cohort`:

| Cohort | Source | Purpose |
|---|---|---|
| `OWN` | Timelines of `@tiptreesystems` and `@martincsweiss1` | Scorecard for Tiptree's own posts |
| `BENCHMARK` | Timelines of the 11 handles in AGENTS.md section 4 | Full per-author history, so within-author baselines are possible |
| `DISCOVERED` | Search across X for researcher posts | Breadth: what works across the ML research community at every account size |

### Definition of a researcher post

> A social media post whose primary audience is actively engaged in publishing, reading, replicating, or stress-testing peer-reviewed scientific literature or empirical machine learning research. It treats the reader as an informed peer rather than a consumer, developer, or enthusiast. It engages with methodological nuance, empirical verification, contested claims, or literature syntheses, rather than high-level commentary, broad tutorials, or product hype.

This definition is about audience and register, which a search query cannot express. Discovery therefore runs in two stages:

1. **Candidate search (wide net).** English posts from the last 180 days matching at least one of: a link to arxiv.org, openreview.net, github.com or huggingface.co; a venue or benchmark name (NeurIPS, ICLR, ICML, ACL, EMNLP, CVPR, SWE-bench); a topic term from a configurable list (ablation, LoRA, tokenizer, fine-tuning, and so on).
2. **Researcher filter (the definition).** The classifier labels each candidate `is_researcher_post` (true or false, with confidence) against the definition above. Only posts labelled true enter the analysis; rejected candidates are kept in the data, flagged, for audit. The hand-labelled set includes this label so the filter is validated like the others.

Two sampling rules matter:

- **Search by "Latest", sliced by date, not by "Top".** "Top" returns posts that already performed well, which selects on the outcome and makes every feature look like a winner.
- **Keep low performers.** No minimum-likes filter at collection. A small floor on author followers (for example 200) removes bots and empty accounts.

## Data source: Apify `apidojo/tweet-scraper`

What the actor page states:

- **Price:** $0.40 per 1,000 posts. About 20,000 posts costs about $8.
- **Input:** X advanced-search queries (`from:handle since:... until:... -filter:retweets lang:en`), handle lists, `sort` of `Latest` or `Top`, `maxItems`.
- **Documented output:** `id`, `url`, `text`, `lang`, `createdAt`, `likeCount`, `retweetCount`, `replyCount`, `quoteCount`, `bookmarkCount`, `isReply`, `isRetweet`, `isQuote`, `quoteId`; author `userName`, `id`, `followers`, `following`, verification flags.
- **Not documented:** a view count, a conversation ID, and a media field for ordinary posts. All three are checked in the test run (open item A).

Usage rules that shape the collector:

- Every query must return at least 50 posts. Low-volume handles are fetched with one wide date range instead of narrow slices, and date slices for discovery are sized to clear 50.
- One concurrent run, up to 5 batched queries per run.
- No single-post fetching and no conversation or reply scraping. Threads are rebuilt only from an author's own posts returned by `from:handle`; if that is not enough, `thread_length` falls back to a text heuristic.
- No re-running the same query at short intervals. The refresh is weekly.
- `customMapFunction` must not be used to filter (the page says this leads to a ban). All filtering happens locally after download.
- Free Apify accounts cannot call the actor through the API.

Risks specific to this route:

- **Terms of service.** X's terms prohibit scraping without consent. The official API costs $0.005 per post read and returns the same public fields; it stays available as a drop-in adapter if this becomes a concern.
- **Field availability varies by actor.** If bookmarks or impressions are missing, `CR_bmk` and `S_intent` cannot be computed. The test run is the gate.
- **Actors break or change output without notice.** Raw output is stored verbatim and the adapter maps field aliases, so a switch of actor only touches one module.
- **No own-post click metrics.** URL clicks and profile clicks exist only through the official API with account sign-in, and only for posts under 30 days old.

## Architecture

Data moves one way. Raw files are stored verbatim and never edited; everything downstream can be rebuilt from them.

```text
Apify actor runs ─► data/raw/ ─► adapters ─► posts.parquet + account_snapshots.parquet
                                                 │
                       ┌─────────────────────────┼────────────────────────┐
                metrics + baselines        rule features          jev classifier (cached)
                       └─────────────────────────┼────────────────────────┘
                                       posts_enriched.parquet
                                                 │
                    lift tables ── swipe file ── findings + templates ── dashboard
```

```text
src/
  schema.py        # Post, AccountSnapshot, PostLabels, enums: the single contract
  config.py        # handles, cohorts, discovery queries, window, thresholds
  ingestion/
    apify.py       # collector; the only module that talks to Apify; writes raw JSONL
    adapters.py    # raw actor JSON or export CSV -> Post, accepting field-name aliases
    load_raw.py    # CLI from AGENTS.md: validate, dedupe, write Parquet, add metrics
  metrics/
    formulas.py    # the three AGENTS.md formulas as pure vectorised functions
    baselines.py   # maturity filter, follower-expected impressions, author medians
  enrichment/
    rules.py       # deterministic features and the hype lint
    judge.py       # rubric, provider-neutral Judge interface, jev implementation
    classify.py    # CLI from AGENTS.md: --model, resumable, cached by label version
    evaluate.py    # hand labels vs judge: agreement report
  analysis/
    lift.py        # lift with confidence intervals and minimum-n gates
    swipe.py       # top-5% selection -> data/swipe_file/
    report.py      # findings and templates, generated from the lift tables
  dashboard.py     # Streamlit, read-only over data/processed
tests/  notebooks/  reports/  docs/  data/{raw,processed,swipe_file,gold}/
```

Setup uses `uv` on Python 3.13 (`requires-python >= 3.11`). AGENTS.md's three run commands stay unchanged. Secrets live in a git-ignored `.env`.

### Posts table

| Group | Columns |
|---|---|
| Identity | `post_id`, `author_handle`, `author_id`, `cohort`, `url`, `created_at`, `collected_at`, `source` |
| Author | `followers_at_collection` (required), `follower_tier` |
| Content | `text`, `post_kind` (original, quote, thread opener), `thread_length`, `media`, `link_kinds` |
| Counts | `impressions`, `likes`, `replies`, `reposts`, `quotes`, `bookmarks` |
| Metrics | `r_out`, `s_intent`, `cr_bmk`, `reach_vs_expected`, `baseline_ratio`, `pctile_in_tier` |
| Rule features | `has_media`, `media_kind`, `has_link`, `char_len`, `has_number`, `mentions_venue`, `has_arxiv_id`, `hype_flags`, `posted_hour_utc` |
| Labels | `hook_archetype`, `visual_type`, `technical_rigor_score`, `label_confidence`, `label_rationale`, `label_version` |

Side tables: `account_snapshots` (follower counts appended on every run) and `labels` (classifier cache keyed by post and label version).

A post without `followers_at_collection` is rejected at ingestion.

## Metrics and method

The three formulas are implemented exactly as in AGENTS.md, including the `max(followers, 100)` and `max(impressions, 1)` floors.

Follower count drives views, but not linearly, so `R_out` alone still favours small accounts' viral posts. Two normalisers handle this:

1. **`reach_vs_expected` (all cohorts).** Fit log(impressions) on log(followers) across the corpus and score each post as actual impressions divided by the impressions expected for an author of that size. This is the main reach metric for `DISCOVERED` posts, where only one or a few posts per author are available.
2. **`baseline_ratio` (`OWN` and `BENCHMARK` only).** Post impressions divided by the author's trailing-30-day median. Possible only where the full timeline is collected.

Other rules:

- **Follower tiers.** Findings are reported per tier (for example under 2k, 2k–20k, 20k–200k, over 200k) so that advice for Tiptree comes from accounts near its size.
- **Eligible posts.** Originals, quote posts and thread openers. Reposts and replies to other people are dropped.
- **Maturity.** A post is scored once it is 7 days old.
- **Follower counts are as of collection.** Each run appends a snapshot so accurate counts exist going forward.
- **Minimum evidence.** A lift is reported only for at least 20 posts from at least 10 distinct authors (3 for within-author comparisons), with a bootstrap confidence interval. Thinner cells show "insufficient data" and cannot produce a recommendation.
- **Intent metrics** (`S_intent`, `CR_bmk`) are already per-impression and are compared within follower tier.

## Enrichment

- **Rules:** media kind, link type, length, numeric claims, venue and benchmark mentions, arXiv IDs, thread length, posting time, and a hype flag for listicle and clickbait patterns that doubles as a lint on generated text.
- **Classifier (Jev):** Jev returns typed values from a predefined output set with calibrated probabilities, which fits enum labels directly. One call per post returns `is_researcher_post`, `hook_archetype` and `technical_rigor_score`, each with its probability stored as `label_confidence`. Listed price is $0.042 per million input tokens with free output, so the whole corpus costs cents. Whether Jev returns free-text rationales is unknown; `label_rationale` is optional.
- **`visual_type` without Jev:** Jev does not accept images. Posts with no media get `NONE` by rule and video gets a rule-based candidate. For still images there are two options, to be chosen at milestone 3: (a) an image-capable model writes a one-line description of each image and Jev classifies that text, or (b) rules plus alt text only, flagged low confidence. Option (a) is the default if a second model is acceptable.
- **Rubric:** anchors for rigor scores 2–4 (AGENTS.md gives only 1 and 5) and precedence rules for overlapping archetypes.
- **Validation:** 150 posts hand-labelled by Ben (including `is_researcher_post`), split into tuning and held-out halves. Proposed bars on the held-out half: Cohen's kappa at least 0.7 for archetype and 0.8 for visual type, rigor within one point on 85% of posts.
- **Mechanics:** labels cached by post and `label_version` (hash of rubric and model). Failures recorded as unlabelled with a reason.

## Outputs

- **Swipe file:** top 5% of mature posts by `reach_vs_expected` within follower tier, which must also sit at or above the tier's median bookmark rate. Hype-flagged and rigor-1 posts are excluded, no author supplies more than 5%, and `curation.csv` lets a person drop entries.
- **Findings report (`reports/findings.md`):** coverage and caveats, findings with interval and sample size, Tiptree's two accounts placed on the distribution for their follower tier, and recommendations for Martin. Each recommendation is generated from a lift row that passed the evidence gate.
- **Post templates:** five to eight structural skeletons (hook pattern, evidence slot, visual spec, call-to-action placement), each with measured lift and three linked examples, each passing the hype lint.
- **Dashboard:** overview, follower-tier and benchmark views, archetype by visual-type lift heatmap, swipe file browser, Tiptree scorecard, recommendations.

## Milestones

| # | Milestone | Needs | Done when |
|---|---|---|---|
| 0 | Scaffold: git, `uv` project, lint and tests, schema, the three formulas, synthetic fixture | Nothing | Tests pass and `load_raw` on the fixture writes metrics matching hand-computed values |
| 1 | Real data: Apify collector, adapters, 50-post test run, timelines for own and benchmark handles, candidate search | Open items A, D | Test run shows impressions, bookmarks and follower counts; coverage table per cohort and tier; 10 posts spot-checked against X |
| 2 | Baselines: maturity filter, follower-expected reach, author medians, tiers | Milestone 1 | Sanity table per tier reviewed |
| 3 | Enrichment: rules, rubric, labelling page, Jev classifier with researcher filter, agreement report | Open items B, C | Held-out bars met and the corpus labelled |
| 4 | Analysis: lift tables, swipe file, findings, templates | Milestones 2–3 | Every number in the findings traces to a lift row |
| 5 | Dashboard | Milestone 4 | All views run on real data and match the report |
| 6 | Weekly refresh (optional) | Milestone 5 | A refresh adds a week without re-collecting old posts |

## Risks

- **Association, not cause.** Lifts are correlations. The real test is Tiptree posting the templates and measuring.
- **Discovery bias.** Keyword search finds posts that use the keywords; researcher posts phrased differently are missed. The query list is versioned in config and reported in the findings.
- **Scraping route** risks are listed under Data source.
- **`@PapersWithCode` is probably dormant.** The handle check in milestone 1 confirms.

## Out of scope for V0

Unsupervised clustering, judging reply quality (replies are counted, not read), automated posting, and platforms other than X.

## Proposed AGENTS.md edits (pending approval)

- Add the two enum values.
- Document cohorts, follower tiers, `reach_vs_expected`, maturity, eligibility and swipe-file rules.
- Replace `gpt-4o-mini` in the example command with the jev model.
- Switch setup commands to `uv`.
- Add `analysis/`, `tests/`, `reports/`, `docs/` and `data/gold/` to the layout.
- Record the own handles `@tiptreesystems` and `@martincsweiss1`.
- Fix the title, which says CLAUDE.md while the file is AGENTS.md.
