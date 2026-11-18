# E7: Small-account breakout vs. polarization

Status: done
Tests: H5 (wording in the project doc).

## Pre-registration

- **Data:** Filter-passing (`is_researcher_post = True`), eligible, mature `ROSTER` (author cap 40) and `PANEL` (author cap 10) posts from accounts with `followers_at_collection < 2500`, `impressions >= 200`, and positive log-reach residual (`reach_vs_expected > 1.0`, fit on `ROSTER`).
- **Arms (`e7_arm`, mutually exclusive):**
  - `G` (`EMPIRICAL_CONTESTED`): `visual_type = PAPER_FIGURE` and `hook_archetype = CONTESTED_CLAIM`.
  - `U` (`UNGROUNDED_HOT_TAKE`): `hook_archetype` in `{HOT_TAKE_CULTURE, CONTESTED_CLAIM}`, `visual_type` in `{NONE, OTHER_IMAGE}`, and `technical_rigor_score <= 2`.
- **Strata:** Follower sub-tier within `<2,500` (`<500`, `500-999`, `1000-2499`), clustered by `author_handle`.
- **Primary tests** (measures in [intent measures](../30_concepts/intent_measures.md); README 99% verdict rule):

  | Test | Measure | Comparison | Prediction |
  |---|---|---|---|
  | H5a | Quote-to-Retweet ratio (`quotes / reposts`) | `U` vs `G` | > 1 |
  | H5b | Bookmark-to-Like ratio (`bookmarks / likes`) | `G` vs `U` | > 1 |
  | H5c | `CR_bmk` (`bookmarks / impressions`) | `G` vs `U` | > 1 |

  `H5c` also reports `U`'s pooled `CR_bmk` and zero-bookmark share (`zero_bmk_share_U`) to check whether ungrounded hot takes exhibit near-zero bookmarks.
- **Secondary:** Same three tests on all `<2,500`-follower posts with `impressions >= 200` without the `reach_vs_expected > 1.0` breakout cut (`H5a-all`, `H5b-all`, `H5c-all`); top-quartile residual sensitivity (`reach_vs_expected >= p75`); unfiltered audience sensitivity (without `is_researcher_post`).
- **Decision:** Each primary test gets its own verdict under the README rule (`RR > 1`, 99% author-clustered bootstrap interval). H5 holds as a whole if `H5a`, `H5b`, and `H5c` are all supported.
- **Feasibility gate & pre-freeze fallback:** At least 20 posts and 10 distinct authors per arm across at least 2 of the 3 sub-tiers (plan decision 61), checked from counts before any outcome is seen. If strict `G` has `<20` posts or `<10` authors in the breakout slice, widen `G` before freeze to `visual_type = PAPER_FIGURE` and `hook_archetype` in `{CONTESTED_CLAIM, TECHNICAL_BREAKDOWN}` with `technical_rigor_score >= 3` (still disjoint from `U`); if still `<20`, drop the `reach_vs_expected > 1.0` cut for the primary test and log an Amendment before freezing.
- **Prerequisites:** Milestone 1–3 v1 corpus with Jev rubric v2 labels (decision 60) and `ROSTER`-fitted `reach_vs_expected` (Milestone 2).
- **Threats:**
  - Low-follower posts often have small `reposts` and `likes` counts; pooling within sub-tier strata avoids zero-denominator post bias, and author-clustered bootstrapping reflects author heterogeneity.
  - Requiring `impressions >= 200` and `reach_vs_expected > 1.0` conditions on reach; the `-all` secondary checks whether the engagement split holds across non-breakout posts too.
  - Because `H5` uses Jev labels directly under decision 60, archetype/rigor misclassifications could attenuate differences between `G` and `U`.

## Amendments

- 2026-11-17 (before freeze): Milestone 3 manual hand-labelling waived under plan decision 60 (`label_version=cf3607061e63`). Outcome-blind feasibility counts on `v1-2026-11-17` (`<2,500` followers, `impressions >= 200`, `ROSTER` cap 40 + `PANEL` cap 10): breakout slice (`reach_vs_expected > 1.0`, `518` total posts) clears all gates under strict `G` (`n_G=21` posts across `14` authors, `n_U=38` posts across `29` authors, `3` contributing sub-tiers `<500`/`500-999`/`1000-2499`), so no widening or breakout relaxation is needed. Unrelaxed `<2,500` secondary slice (`636` total posts): `n_G=23` (`14` authors), `n_U=47` (`31` authors), `3` sub-tiers.

## Runs

- 2026-11-17, commit `99464bb`, data `v1-2026-11-17`, labels `cf3607061e63`: `<2,500`-follower breakout slice (`518` total posts; `59` posts in strict `G=21` [14 au] vs `U=38` [29 au] across `42` distinct authors and `3` sub-tiers `<500`, `500-999`, `1000-2499`). Log: `outputs/runs/E7_2026-11-17.log`.
  - `H5a` (Quote/Retweet ratio `U` vs `G`): `1.2340` (`99% CI [0.1630, 4.9390]`, `n=59`, `au=42`, `strata=3`) → `inconclusive`; `NC-H5a`: `1.1853 [0.3173, 10.6487]` (`control`).
  - `H5b` (Bookmark/Like ratio `G` vs `U`): `2.6708` (`99% CI [0.6722, 7.4126]`, `n=59`, `au=42`, `strata=3`) → `inconclusive`; `NC-H5b`: `0.4738 [0.2800, 2.1497]` (`control`).
  - `H5c` (`CR_bmk` `G` vs `U`): `3.5577` (`99% CI [0.5270, 9.0379]`, `n=59`, `au=42`, `strata=3`) → `inconclusive`; `U cr_bmk = 1.57`, `zero_bmk_share_U = 0.34`; `NC-H5c`: `0.7646 [0.4143, 4.8697]` (`control`).
  - Secondary (`all<2500`, `636` total, `70` arm posts, `44` au, `3` strata): `H5a-all = 1.1948 [0.1381, 4.4001]`, `H5b-all = 2.6600 [0.6840, 7.2334]`, `H5c-all = 3.5476 [0.4776, 9.0150]`.

## Verdict

- **`H5` is inconclusive across `H5a`, `H5b`, and `H5c`:** Every comparison points in the hypothesized direction — `G` (`PAPER_FIGURE + CONTESTED_CLAIM`) earns `3.56x` the bookmark rate (`CR_bmk`) and `2.67x` the bookmark-to-like ratio of ungrounded hot takes (`U`, where `CR_bmk = 1.57` and `34%` earn zero bookmarks), while `U` shows `1.23x` Quote-to-Retweet polarization — and all three negative controls passed, but at `n = 59` (`42` authors) the 99% author-clustered bootstrap intervals span 1. Larger small-account samples are needed to test H5 at 99% confidence.
