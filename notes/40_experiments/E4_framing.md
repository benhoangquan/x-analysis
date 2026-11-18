# E4: Question, claim or curiosity gap

Status: done
Tests: H4 (wording in the project doc).

## Pre-registration

- **Data:** `ROSTER` posts that are filter-passing, eligible, mature and inside the author cap. `OWN` and `BENCHMARK` are excluded.
- **Arms:** [`framing`](../30_concepts/framing.md): `OPEN_QUESTION`, `DECLARATIVE_EMPIRICAL`, `DECLARATIVE_OTHER`, `CURIOSITY_GAP`.
- **Strata:** author. Each comparison is within one account, which holds followers, prestige and audience constant.
- **Primary tests** (measures defined in [intent measures](../30_concepts/intent_measures.md)):

  | Test | Measure | Comparison | Prediction |
  |---|---|---|---|
  | H4a | replies per impression, thread openers left out | `OPEN_QUESTION` vs `DECLARATIVE_EMPIRICAL` ∪ `DECLARATIVE_OTHER` | > 1 |
  | H4b | bookmarks per like | `DECLARATIVE_EMPIRICAL` vs `OPEN_QUESTION` | > 1 |
  | H4c | `CR_bmk` | `CURIOSITY_GAP` vs `DECLARATIVE_EMPIRICAL` | no lift (null prediction) |

- **Secondary:** the same tests across authors with follower-tier strata; the under-2k tier alone; H4c on all roster posts without the researcher filter, labelled exploratory.
- **Decision:** README verdict rule; H4c uses the null-prediction column.
- **Feasibility gate:** at least 20 authors with posts in both arms of each test, counted before the freeze. In v0, 18 of 122 researcher posts contained "?" and none had a curiosity-gap phrase (5 of 1,428 eligible posts overall). H4c may well end `insufficient`; that is a result, and the data is not widened to avoid it.
- **Prerequisites:** milestone 1 roster; `framing` at Cohen's kappa ≥ 0.7 (plan decision 30); thread openers flagged by text cues (plan decision 36).
- **Threats:**
  - Replies are counted, not read. A question may draw social replies, not technical ones, and H4a cannot tell them apart.
  - Replies are not collected, so the author's own replies cannot be subtracted. Thread openers are left out of H4a; an author replying under a single post still counts.
  - An author's questions may be on different topics from their claims. Rigor and archetype mix per arm are reported.

AGENTS.md §7 rules out recommending curiosity-gap hooks. Whatever H4c shows is reported as a finding and never becomes a template.

## Amendments

- 2026-11-14 (draft, before freeze): H4a leaves out thread openers instead of subtracting own replies, because replies are no longer collected (plan decision 36).

- 2026-11-17 (before freeze): Milestone 3 manual hand-labelling waived under plan decision 60 (`label_version=cf3607061e63`). Outcome-blind feasibility counts on `v1-2026-11-17` (`1,537` filter-passing capped `ROSTER` posts across `191` authors; `1,486` non-thread-openers; `DECLARATIVE_OTHER=1,124`, `DECLARATIVE_EMPIRICAL=299`, `CURIOSITY_GAP=58`, `OPEN_QUESTION=56`): all three within-author tests clear `>=20` posts/arm, `>=10` authors/arm, and `>=20` contributing author strata (`H4a`: `56`/`1,380` posts, `37`/`182` authors, `36` strata; `H4b`: `299`/`56` posts, `88`/`37` authors, `25` strata; `H4c`: `58`/`299` posts, `42`/`88` authors, `22` strata).

## Runs

- 2026-11-12, `dry_run` on v0 (rule-proxy framing, 38–49 posts, 0–1 strata): harness check only; see ledger and daily log. Not evidence.
- 2026-11-17, commit `e594ea9`, data `v1-2026-11-17`, labels `cf3607061e63`: `1,537` filter-passing capped `ROSTER` posts across `191` authors (`1,486` non-openers). Log: `outputs/runs/E4_2026-11-17.log`.
  - `H4a` (replies/impression, `OPEN_QUESTION` vs `DECLARATIVE_*`, non-openers, `36` author strata): `1.2518` (`99% CI [0.8995, 2.2922]`, `n=1,436`, `au=183`) → `inconclusive`; `NC-H4a`: `0.7579 [0.4426, 1.1602]` (`control`).
  - `H4b` (bookmarks/like, `DECLARATIVE_EMPIRICAL` vs `OPEN_QUESTION`, `25` author strata): `0.9542` (`99% CI [0.6013, 1.7757]`, `n=355`, `au=100`) → `inconclusive`; `NC-H4b`: `1.1849 [0.8273, 1.8221]` (`control`).
  - `H4c` (`CR_bmk`, `CURIOSITY_GAP` vs `DECLARATIVE_EMPIRICAL`, `22` author strata): `0.7028` (`99% CI [0.2712, 1.9581]`, `n=357`, `au=108`) → `inconclusive`; `NC-H4c`: `0.7841 [0.4366, 2.0535]` (`control`).

## Verdict

- **`H4` is inconclusive across all three tests:** All three within-author tests cleared `>=20` contributing author strata and all negative controls passed, but the 99% author-clustered bootstrap intervals span 1 (`H4a=1.25 [0.90, 2.29]`, `H4b=0.95 [0.60, 1.78]`, `H4c=0.70 [0.27, 1.96]`). On `H4c`, the `0.70x` point estimate suggests no lift from curiosity-gap framing, though the upper bound (`1.96x`) does not clear the `<1.2x` null-confirmation threshold. Inconclusive means no large within-author effect was detected at these sample sizes.
