# E3: Do controllable features predict top-half posts?

Status: draft
Tests: H3 (wording in the project doc).

## Pre-registration

- **Data:** paper-linked, filter-passing, eligible, mature posts: roster posts that link an arXiv paper (author cap 40) plus the [paper panel](../30_concepts/paper_panel.md) (cap 10). Paper-linked posts are used because H3 names paper substance and author prestige, which exist only when a post links a paper.
- **Target:** `top_half`: `cr_bmk_shrunk` above its follower tier's median in this data set.
- **Feature blocks:**
  - Controls C: log followers, follower tier, [poster role](../30_concepts/poster_role.md), paper-author prestige (highest Semantic Scholar h-index among the linked paper's authors).
  - Controllable X: paper substance (arXiv primary category, code link, venue acceptance, paper age at posting); visual (`visual_type`); copy (`hook_archetype`, [`framing`](../30_concepts/framing.md), `technical_rigor_score`, length, numbers, venue mention, thread length, hype flags, posting hour).
- **Models:** M0 = logistic regression on C. M1 = logistic regression on C + X. L2 penalty with C = 1, standardised numbers, one-hot categories. Logistic regression is the simplest model that takes mixed features and yields a probability.
- **Validation:** out-of-fold predictions from 5-fold cross-validation grouped by author (no author appears in both train and test), repeated with 5 fold seeds.
- **Primary test:** H3: ΔAUC = AUC(M1) − AUC(M0). 99% interval from a paired author bootstrap of the out-of-fold predictions. Permutation null: X rows shuffled within tier, 200 times.
- **Decision:**
  - `supported`: ΔAUC ≥ 0.03, 99% lower bound > 0, ΔAUC above the permutation null's 99th percentile, and AUC(M1) ≥ 0.60.
  - `refuted`: 99% upper bound < 0.02.
  - `inconclusive`: anything else.
  - `insufficient`: fewer than 400 posts or 80 authors.

  The 0.03 and 0.60 bars are judgment calls, fixed here before the data.
- **Secondary:** block importance (ΔAUC when the paper, visual or copy block is dropped from M1), which feeds E5; gradient-boosted trees on C + X, reported only (they replace logistic regression only in a later, separately frozen run, and only if they beat it by 0.02 AUC); a within-author target, `cr_bmk_shrunk` above the author's own median, which removes author effects entirely.
- **Feasibility gate:** at least 400 posts from 80 authors, counted before the freeze.
- **Prerequisites:** E1's inputs (panel, poster role); `framing` (E4); paper metadata from arXiv and Semantic Scholar, and scikit-learn (plan decision 32).
- **Threats:**
  - h-index matching errors between arXiv names and Semantic Scholar authors; 30 matches are spot-checked.
  - Shrinkage pulls low-view posts toward the tier rate, so small-account posts crowd the median. Class balance per tier is reported.
  - Prediction is not causation: a supported H3 says the features carry signal, not that changing them causes lift. The posting experiment tests that.

## Amendments

## Runs

## Verdict
