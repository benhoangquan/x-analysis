# E1: Poster credentials, reach vs intent

Status: done
Tests: H1 (wording in the project doc). "Poster tier" is [poster role](../30_concepts/poster_role.md): original researcher, credentialed researcher, or neither (plan decision 30; classes redefined 2026-11-14).

## Pre-registration

- **Data:** the [paper panel](../30_concepts/paper_panel.md): eligible, mature posts that link a panel paper, at most 10 per author. The researcher filter is not applied (plan decision 31), because non-researchers write for the general public; the share of filter-passing posts is reported per role.
- **Arms:** `poster_role` per post: `ORIGINAL_RESEARCHER`, `CREDENTIALED_RESEARCHER`, `NON_RESEARCHER`. H1's "hype explainers" are the `NON_RESEARCHER` arm.
- **Strata:** paper. Every comparison holds the paper constant.
- **Primary tests:**

  | Test | Measure | Comparison | Prediction |
  |---|---|---|---|
  | H1a | impressions: geometric-mean ratio within paper | `NON_RESEARCHER` vs `ORIGINAL_RESEARCHER` and `CREDENTIALED_RESEARCHER` pooled | > 1 |
  | H1b-O | `S_intent`: stratified rate ratio | `ORIGINAL_RESEARCHER` vs `NON_RESEARCHER` | > 1 |
  | H1b-C | `S_intent`: stratified rate ratio | `CREDENTIALED_RESEARCHER` vs `NON_RESEARCHER` | > 1 |

  `S_intent` is the AGENTS.md formula, replies counted as they are. H1a is not a rate: the estimator is the mean over papers of the within-paper difference in mean log impressions, exponentiated, with a paper bootstrap. H1b uses the stratified rate ratio from the [README](README.md), with the weighted count as numerator and impressions as exposure.
- **Secondary:** likes (as H1a); `CR_bmk` (as H1b); `S_intent` for `ORIGINAL_RESEARCHER` vs `CREDENTIALED_RESEARCHER`; follower-adjusted reach, with strata of paper x follower tier, to show how much of H1a is account size; within `NON_RESEARCHER`, hype-flagged vs unflagged posts; posting order within the paper (first 24 hours vs later) by role.
- **Decision:** each test gets its own verdict under the README rule, and the project doc lists all three. H1 holds as a whole only if all three are supported. If H1a holds on raw impressions but not within paper x tier, the finding reads "non-researchers are larger accounts", not "non-researcher framing earns reach".
- **Feasibility gate:** at least 20 papers holding both a `NON_RESEARCHER` and an `ORIGINAL_RESEARCHER` post (H1b-O), and 20 holding `NON_RESEARCHER` and `CREDENTIALED_RESEARCHER` (H1b-C). If a gate fails, the panel grows once, from the reserve, by up to 100 papers (about $0.75) before the freeze; if it still fails, that test is pre-registered as `insufficient`.
- **Prerequisites:** paper panel (plan decision 29); `poster_role` with Cohen's kappa >= 0.7 on 100 hand-labelled paper-linked posts and a 50-post check of author name matches (decision 30); Ben's confirmation of the credential rule; milestone 2 metrics computed on panel posts.
- **Threats:**
  - Non-researchers are mostly large accounts, so raw reach is confounded with followers by design. The paper x tier secondary measures how much.
  - Credentials are matched by name and bio; matching errors move accounts between the two researcher classes. 50 matches are spot-checked.
  - Panel papers are ones researchers link, kept only when several accounts posted them. Results describe shared papers, not arXiv at large.
  - Authors often post first and others later; the first post may take the attention. The posting-order secondary checks this.
  - Bookmark and reply rates differ by audience. That difference is part of what H1 claims, so it is not adjusted away.

## Amendments

- 2026-11-14 (draft, before freeze; plan decision 43): the primary tests become cross-paper. H1a, H1b-O and H1b-C compare roles over all paper-linked posts (roster and panel), with strata of follower tier × arXiv primary category and an author bootstrap. The within-paper versions move to Secondary. Reason: the 200-paper panel had 6 papers with an author post and another poster, against a gate of 20. For the cross-paper tests the README gate's "20 contributing strata" becomes 5, since tier × category has at most about 30 cells; posts and authors per arm stay at 20 and 10 (accepted by Ben, plan decision 50).

- 2026-11-14 (draft, before freeze): panel growth fallback cut to 100 papers to fit the $10 cap (plan decision 36).
- 2026-11-14 (draft, before freeze): roles redefined by credentials instead of hype or curation; primary measure changed from `CR_bmk` to `S_intent` (Ben).

- 2026-11-17 (before freeze): Milestone 3 manual hand-labelling waived under plan decision 60 (`label_version=cf3607061e63`, `role_version=55945d80ebf0`). Outcome-blind feasibility counts on `v1-2026-11-17` (`734` capped paper-linked posts across `372` authors; roles `NON_RESEARCHER=372`, `ORIGINAL_RESEARCHER=287`, `CREDENTIALED_RESEARCHER=75`; filter-passing shares `98.6%`, `96.0%`, `86.6%`): cross-paper `tier_cat` strata (`min_strata=5`) clear all gates (`H1a`: `372`/`362` posts, `182`/`198` authors, `25` strata; `H1b-O`: `287`/`372` posts, `176`/`182` authors, `18` strata; `H1b-C`: `75`/`372` posts, `33`/`182` authors, `21` strata). Within-paper secondary strata (`min_strata=20`): `H1a-wp=37`, `H1b-O-wp=31`, `H1b-C-wp=13` (`insufficient`).

## Runs

- 2026-11-17, commit `bbf6b51`, data `v1-2026-11-17`, labels `cf3607061e63` (`role_version=55945d80ebf0`): `734` capped paper-linked posts across `372` authors (`NON_RESEARCHER=372`, `ORIGINAL_RESEARCHER=287`, `CREDENTIALED_RESEARCHER=75`). Log: `outputs/runs/E1_2026-11-17.log`.
  - `H1a` (impressions GM ratio, `NON_RESEARCHER` vs researchers, `tier_cat`, `n_strata=25`): `0.2048` (`99% CI [0.0854, 0.3510]`, `n=734`, `au=372`) → `refuted`; negative control `NC-H1a`: `0.8664 [0.6295, 1.4403]` (`control`).
  - `H1b-O` (`S_intent` RR, `ORIGINAL_RESEARCHER` vs `NON_RESEARCHER`, `tier_cat`, `n_strata=18`): `0.9045` (`99% CI [0.6717, 1.3194]`, `n=659`, `au=353`) → `inconclusive`; `NC-H1b-O`: `1.0792 [0.7868, 1.5243]` (`control`).
  - `H1b-C` (`S_intent` RR, `CREDENTIALED_RESEARCHER` vs `NON_RESEARCHER`, `tier_cat`, `n_strata=21`): `1.5720` (`99% CI [0.8319, 2.5358]`, `n=447`, `au=212`) → `inconclusive`; `NC-H1b-C`: `1.0014 [0.6519, 2.0860]` (`control`).
  - Secondary within-paper (`first_paper_id`): `H1a-wp=0.0893 [0.0388, 0.2259]` (`37` strata), `H1b-O-wp=0.7711 [0.5568, 1.1681]` (`31` strata), `H1b-C-wp=0.7557 [0.3627, 1.5693]` (`13` strata, gate failed).

## Verdict

- **`H1` is refuted overall:** `H1a` is cleanly **refuted** (`0.2048`, `99% CI [0.0854, 0.3510]`; within-paper `0.0893`), the opposite of the prediction — non-researchers earn roughly one-fifth the impressions of paper authors and credentialed researchers even within `tier × category` strata. Both high-intent rate comparisons (`H1b-O=0.9045`, `H1b-C=1.5720`) are `inconclusive` at 99% confidence. All three negative controls passed.
