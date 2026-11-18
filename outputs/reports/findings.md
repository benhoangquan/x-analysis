# Tiptree X Analytics Findings

- **Query version:** `v1`
- **Label version:** `cf3607061e63`
- **Filler items dropped at ingestion:** 1780

> **Note (Decision 60):** Ben waived the Milestone 3 manual post hand-labelling checks; lift tables, recommendations, and templates below use Jev rubric v2 labels directly without held-out human kappa verification. Statistical cell gates (>=20 posts, >=10 authors) remain enforced.

## Corpus coverage

| cohort | follower_tier | posts | eligible | mature | authors | researcher_posts |
|---|---|---|---|---|---|---|
| BENCHMARK | 2k-20k | 5 | 5 | 5 | 1 | 0 |
| BENCHMARK | 20k-200k | 9 | 9 | 9 | 1 | 6 |
| BENCHMARK | >200k | 18 | 18 | 18 | 1 | 13 |
| OWN | <2k | 27 | 27 | 27 | 2 | 20 |
| PANEL | <2k | 142 | 142 | 142 | 117 | 118 |
| PANEL | 2k-20k | 100 | 100 | 100 | 72 | 84 |
| PANEL | 20k-200k | 43 | 43 | 43 | 20 | 39 |
| PANEL | >200k | 1 | 1 | 1 | 1 | 1 |
| ROSTER | <2k | 1245 | 1245 | 1245 | 122 | 768 |
| ROSTER | 2k-20k | 4395 | 4395 | 4395 | 48 | 2934 |
| ROSTER | 20k-200k | 2472 | 2472 | 2472 | 17 | 916 |
| ROSTER | >200k | 203 | 203 | 203 | 5 | 145 |

## Tiptree scorecard (`<2k` benchmark)

`<2k` tier distribution (`cr_bmk_shrunk`, n=1414): p25=2.86, median=3.28, p75=4.09, p90=6.79 bookmarks/1k views.

| account | mature_posts | median_views | median_cr_bmk | median_cr_bmk_shrunk | pctile_in_under_2k |
|---|---|---|---|---|---|
| @tiptreesystems | 8 | 122 | 0.00 | 3.31 | 52% |
| @martincsweiss1 | 19 | 237 | 0.00 | 3.04 | 33% |

## Lift tables (filter-passing, capped corpus)

### By follower tier × `hook_archetype`

| follower_tier | hook_archetype | n_posts | n_authors | cr_bmk_ci | lift_ci | evidence |
|---|---|---|---|---|---|---|
| <2k | CONTESTED_CLAIM | 120 | 64 | 5.26 [3.87, 7.74] | 1.45x [0.95, 2.32] | ok |
| <2k | OTHER | 366 | 161 | 4.23 [3.37, 5.34] | 1.17x [0.83, 1.73] | ok |
| <2k | PRODUCT_DEMO | 122 | 69 | 1.84 [0.76, 6.70] | 0.51x [0.28, 1.43] | ok |
| <2k | HOT_TAKE_CULTURE | 25 | 15 | 1.26 [0.30, 5.32] | 0.35x [0.08, 1.57] | ok |
| <2k | TECHNICAL_BREAKDOWN | 7 | 6 | insufficient data | insufficient data | insufficient data |
| <2k | VISUAL_MAP | 14 | 13 | insufficient data | insufficient data | insufficient data |
| 2k-20k | VISUAL_MAP | 26 | 19 | 6.21 [4.58, 10.24] | 1.23x [0.86, 2.04] | ok |
| 2k-20k | PRODUCT_DEMO | 121 | 39 | 6.02 [4.68, 8.78] | 1.19x [0.88, 1.74] | ok |
| 2k-20k | OTHER | 439 | 82 | 5.32 [3.57, 7.39] | 1.05x [0.86, 1.26] | ok |
| 2k-20k | CONTESTED_CLAIM | 169 | 47 | 3.84 [3.42, 4.68] | 0.76x [0.62, 0.99] | ok |
| 2k-20k | TECHNICAL_BREAKDOWN | 14 | 11 | insufficient data | insufficient data | insufficient data |
| 2k-20k | HOT_TAKE_CULTURE | 10 | 8 | insufficient data | insufficient data | insufficient data |
| 20k-200k | PRODUCT_DEMO | 44 | 18 | 5.43 [1.46, 9.74] | 1.26x [0.49, 1.95] | ok |
| 20k-200k | CONTESTED_CLAIM | 57 | 19 | 4.75 [3.02, 8.04] | 1.10x [0.70, 1.77] | ok |
| 20k-200k | OTHER | 151 | 25 | 3.97 [2.16, 6.32] | 0.92x [0.64, 1.23] | ok |
| 20k-200k | VISUAL_MAP | 6 | 3 | insufficient data | insufficient data | insufficient data |
| 20k-200k | TECHNICAL_BREAKDOWN | 7 | 2 | insufficient data | insufficient data | insufficient data |
| 20k-200k | LITERATURE_SYNTHESIS | 1 | 1 | insufficient data | insufficient data | insufficient data |
| 20k-200k | HOT_TAKE_CULTURE | 6 | 5 | insufficient data | insufficient data | insufficient data |
| >200k | VISUAL_MAP | 6 | 2 | insufficient data | insufficient data | insufficient data |
| >200k | PRODUCT_DEMO | 21 | 5 | insufficient data | insufficient data | insufficient data |
| >200k | CONTESTED_CLAIM | 11 | 5 | insufficient data | insufficient data | insufficient data |
| >200k | HOT_TAKE_CULTURE | 1 | 1 | insufficient data | insufficient data | insufficient data |
| >200k | OTHER | 73 | 6 | insufficient data | insufficient data | insufficient data |
| >200k | TECHNICAL_BREAKDOWN | 1 | 1 | insufficient data | insufficient data | insufficient data |

### By follower tier × `visual_type`

| follower_tier | visual_type | n_posts | n_authors | cr_bmk_ci | lift_ci | evidence |
|---|---|---|---|---|---|---|
| <2k | PAPER_FIGURE | 98 | 65 | 6.55 [4.35, 8.52] | 1.81x [1.19, 2.70] | ok |
| <2k | VIDEO_DEMO | 63 | 38 | 4.29 [3.07, 5.98] | 1.18x [0.76, 1.87] | ok |
| <2k | OTHER_IMAGE | 115 | 56 | 3.70 [2.22, 5.75] | 1.02x [0.58, 1.73] | ok |
| <2k | NONE | 377 | 154 | 2.39 [1.24, 5.09] | 0.66x [0.46, 1.03] | ok |
| <2k | LACUNA_MAP | 1 | 1 | insufficient data | insufficient data | insufficient data |
| 2k-20k | PAPER_FIGURE | 112 | 43 | 6.78 [5.36, 9.21] | 1.34x [1.02, 1.87] | ok |
| 2k-20k | VIDEO_DEMO | 41 | 16 | 6.71 [4.77, 9.81] | 1.32x [0.98, 1.95] | ok |
| 2k-20k | OTHER_IMAGE | 276 | 40 | 5.47 [4.42, 6.75] | 1.08x [0.83, 1.45] | ok |
| 2k-20k | NONE | 349 | 68 | 3.45 [2.38, 5.18] | 0.68x [0.52, 0.90] | ok |
| 2k-20k | CODE_TERMINAL | 1 | 1 | insufficient data | insufficient data | insufficient data |
| 20k-200k | OTHER_IMAGE | 89 | 16 | 5.90 [3.30, 10.14] | 1.37x [0.81, 2.20] | ok |
| 20k-200k | PAPER_FIGURE | 69 | 18 | 5.55 [3.04, 9.33] | 1.29x [0.82, 2.00] | ok |
| 20k-200k | NONE | 99 | 21 | 3.70 [2.67, 6.32] | 0.86x [0.63, 1.35] | ok |
| 20k-200k | VIDEO_DEMO | 12 | 6 | insufficient data | insufficient data | insufficient data |
| 20k-200k | LACUNA_MAP | 1 | 1 | insufficient data | insufficient data | insufficient data |
| 20k-200k | CODE_TERMINAL | 2 | 2 | insufficient data | insufficient data | insufficient data |
| >200k | VIDEO_DEMO | 33 | 3 | insufficient data | insufficient data | insufficient data |
| >200k | PAPER_FIGURE | 19 | 5 | insufficient data | insufficient data | insufficient data |
| >200k | OTHER_IMAGE | 31 | 5 | insufficient data | insufficient data | insufficient data |
| >200k | NONE | 30 | 4 | insufficient data | insufficient data | insufficient data |

### By follower tier × `framing`

| follower_tier | framing | n_posts | n_authors | cr_bmk_ci | lift_ci | evidence |
|---|---|---|---|---|---|---|
| <2k | OPEN_QUESTION | 27 | 22 | 6.19 [1.99, 7.71] | 1.71x [0.53, 2.61] | ok |
| <2k | CURIOSITY_GAP | 33 | 30 | 5.47 [3.74, 7.19] | 1.51x [1.00, 2.19] | ok |
| <2k | DECLARATIVE_EMPIRICAL | 120 | 64 | 4.98 [3.66, 6.59] | 1.38x [0.88, 2.14] | ok |
| <2k | DECLARATIVE_OTHER | 474 | 179 | 3.01 [1.85, 5.04] | 0.83x [0.70, 0.99] | ok |
| 2k-20k | DECLARATIVE_OTHER | 576 | 94 | 6.00 [4.94, 7.19] | 1.18x [1.02, 1.45] | ok |
| 2k-20k | DECLARATIVE_EMPIRICAL | 143 | 43 | 4.30 [2.38, 7.20] | 0.85x [0.53, 1.30] | ok |
| 2k-20k | OPEN_QUESTION | 30 | 19 | 3.27 [1.73, 4.99] | 0.65x [0.33, 0.98] | ok |
| 2k-20k | CURIOSITY_GAP | 30 | 22 | 3.22 [1.66, 7.46] | 0.64x [0.33, 1.35] | ok |
| 20k-200k | DECLARATIVE_OTHER | 195 | 27 | 4.53 [2.51, 7.06] | 1.05x [0.81, 1.31] | ok |
| 20k-200k | DECLARATIVE_EMPIRICAL | 58 | 18 | 3.56 [2.38, 6.22] | 0.83x [0.59, 1.24] | ok |
| 20k-200k | CURIOSITY_GAP | 10 | 5 | insufficient data | insufficient data | insufficient data |
| 20k-200k | OPEN_QUESTION | 9 | 6 | insufficient data | insufficient data | insufficient data |
| >200k | DECLARATIVE_EMPIRICAL | 31 | 5 | insufficient data | insufficient data | insufficient data |
| >200k | DECLARATIVE_OTHER | 79 | 6 | insufficient data | insufficient data | insufficient data |
| >200k | OPEN_QUESTION | 2 | 2 | insufficient data | insufficient data | insufficient data |
| >200k | CURIOSITY_GAP | 1 | 1 | insufficient data | insufficient data | insufficient data |

## Actionable recommendations for Martin

- In `<2k`, posts with `visual_type=PAPER_FIGURE` achieve **1.81x** higher bookmark rate (95% CI [1.19, 2.70], CR_bmk=6.55 vs tier 3.62; n=98 posts across 65 authors).
- In `2k-20k`, posts with `framing=DECLARATIVE_OTHER` achieve **1.18x** higher bookmark rate (95% CI [1.02, 1.45], CR_bmk=6.00 vs tier 5.06; n=576 posts across 94 authors).
- In `2k-20k`, posts with `visual_type=PAPER_FIGURE` achieve **1.34x** higher bookmark rate (95% CI [1.02, 1.87], CR_bmk=6.78 vs tier 5.06; n=112 posts across 43 authors).

## Post templates (evidence-gated)

### Template: `<2k` × `visual_type=PAPER_FIGURE`
- **Hook pattern:** Pair a concise empirical claim with a paper figure asset
- **Evidence slot:** Cite one ablation metric, baseline comparison, or contradiction from the paper.
- **Visual spec:** PAPER_FIGURE
- **Call-to-action placement:** End with a direct link to the paper or Lacuna topology and an open technical question.
- **Measured lift:** 1.81x tier baseline (95% CI [1.19, 2.70], pooled CR_bmk 6.55, n=98 posts, 65 authors)
- **Examples:** [2103091287289106910](https://x.com/hooshaaii/status/2103091287289106910), [2100293181174653301](https://x.com/hooshaaii/status/2100293181174653301), [2103077574373249236](https://x.com/hooshaaii/status/2103077574373249236)

### Template: `2k-20k` × `framing=DECLARATIVE_OTHER`
- **Hook pattern:** Pair a concise empirical claim with a declarative other asset
- **Evidence slot:** Cite one ablation metric, baseline comparison, or contradiction from the paper.
- **Visual spec:** PAPER_FIGURE or LACUNA_MAP (when matching claim)
- **Call-to-action placement:** End with a direct link to the paper or Lacuna topology and an open technical question.
- **Measured lift:** 1.18x tier baseline (95% CI [1.02, 1.45], pooled CR_bmk 6.00, n=576 posts, 94 authors)
- **Examples:** [2086336870452166922](https://x.com/Zen_with_AI/status/2086336870452166922), [2107911620399931524](https://x.com/SophieLWang/status/2107911620399931524), [2103910269982474516](https://x.com/arXivBangers/status/2103910269982474516)

### Template: `2k-20k` × `visual_type=PAPER_FIGURE`
- **Hook pattern:** Pair a concise empirical claim with a paper figure asset
- **Evidence slot:** Cite one ablation metric, baseline comparison, or contradiction from the paper.
- **Visual spec:** PAPER_FIGURE
- **Call-to-action placement:** End with a direct link to the paper or Lacuna topology and an open technical question.
- **Measured lift:** 1.34x tier baseline (95% CI [1.02, 1.87], pooled CR_bmk 6.78, n=112 posts, 43 authors)
- **Examples:** [2103910269982474516](https://x.com/arXivBangers/status/2103910269982474516), [2117878218657300585](https://x.com/arXivBangers/status/2117878218657300585), [2112881607279263767](https://x.com/mkirchhof_/status/2112881607279263767)
