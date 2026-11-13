# E1: Poster role, reach vs intent

Status: draft
Tests: H1 (wording in the project doc). "Poster tier" is read as [poster role](../30_concepts/poster_role.md) (plan decision 30).

## Pre-registration

- **Data:** the [paper panel](../30_concepts/paper_panel.md): eligible, mature posts that link a panel paper, at most 10 per author. The researcher filter is not applied (plan decision 31), because hype explainers write for the general public; the share of filter-passing posts is reported per role.
- **Arms:** `poster_role` per post: `PAPER_AUTHOR`, `NEUTRAL_CURATOR`, `HYPE_EXPLAINER`. `COMMENTATOR` posts are described, not tested.
- **Strata:** paper. Every comparison holds the paper constant.
- **Primary tests:**

  | Test | Measure | Comparison | Prediction |
  |---|---|---|---|
  | H1a | impressions: geometric-mean ratio of within-paper impressions | `HYPE_EXPLAINER` vs `PAPER_AUTHOR` ∪ `NEUTRAL_CURATOR` | > 1 |
  | H1b-A | `CR_bmk`: stratified rate ratio, bookmarks per impression | `PAPER_AUTHOR` vs `HYPE_EXPLAINER` | > 1 |
  | H1b-C | `CR_bmk`: stratified rate ratio, bookmarks per impression | `NEUTRAL_CURATOR` vs `HYPE_EXPLAINER` | > 1 |

  H1a is not a rate, so its estimator is the mean over papers of the within-paper difference in mean log impressions, exponentiated, with a paper bootstrap. H1b uses the stratified rate ratio from the [README](README.md).
- **Secondary:** likes (as H1a); `S_intent` (as H1b, weighted counts); follower-adjusted reach, with strata of paper × follower tier, to show how much of H1a is account size; posting order within the paper (first 24 hours vs later) by role; account-level roles.
- **Decision:** each test gets its own verdict under the README rule, and the project doc lists all three. H1 holds as a whole only if all three are supported. If H1a holds on raw impressions but not within paper × tier, the finding reads "hype explainers are larger accounts", not "hype framing earns reach".
- **Feasibility gate:** at least 20 papers holding both a `HYPE_EXPLAINER` and a `PAPER_AUTHOR` post (H1b-A), and 20 holding `HYPE_EXPLAINER` and `NEUTRAL_CURATOR` (H1b-C). If a gate fails, the panel grows once by another 300 papers (about $2) before the freeze; if it still fails, that test is pre-registered as `insufficient`.
- **Prerequisites:** paper panel (plan decision 29); `poster_role` with Cohen's kappa ≥ 0.7 on 100 hand-labelled paper-linked posts and a 50-post check of author name matches (decision 30); milestone 2 metrics computed on panel posts.
- **Threats:**
  - Hype explainers are mostly large accounts, so raw reach is confounded with followers by design. The paper × tier secondary measures how much.
  - Panel papers are ones researchers link, kept only when several accounts posted them. Results describe shared papers, not arXiv at large.
  - Authors often post first and explainers later; the first post may take the attention. The posting-order secondary checks this.
  - Bookmark rates differ by audience. That difference is part of what H1 claims, so it is not adjusted away.

## Amendments

## Runs

## Verdict
