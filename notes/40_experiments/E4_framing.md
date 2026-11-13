# E4: Question, claim or curiosity gap

Status: draft
Tests: H4 (wording in the project doc).

## Pre-registration

- **Data:** `ROSTER` posts that are filter-passing, eligible, mature and inside the author cap. `OWN` and `BENCHMARK` are excluded.
- **Arms:** [`framing`](../30_concepts/framing.md): `OPEN_QUESTION`, `DECLARATIVE_EMPIRICAL`, `DECLARATIVE_OTHER`, `CURIOSITY_GAP`.
- **Strata:** author. Each comparison is within one account, which holds followers, prestige and audience constant.
- **Primary tests** (measures defined in [intent measures](../30_concepts/intent_measures.md)):

  | Test | Measure | Comparison | Prediction |
  |---|---|---|---|
  | H4a | other people's replies per impression | `OPEN_QUESTION` vs `DECLARATIVE_EMPIRICAL` ∪ `DECLARATIVE_OTHER` | > 1 |
  | H4b | bookmarks per like | `DECLARATIVE_EMPIRICAL` vs `OPEN_QUESTION` | > 1 |
  | H4c | `CR_bmk` | `CURIOSITY_GAP` vs `DECLARATIVE_EMPIRICAL` | no lift (null prediction) |

- **Secondary:** the same tests across authors with follower-tier strata; the under-2k tier alone; H4c on all roster posts without the researcher filter, labelled exploratory.
- **Decision:** README verdict rule; H4c uses the null-prediction column.
- **Feasibility gate:** at least 20 authors with posts in both arms of each test, counted before the freeze. In v0, 18 of 122 researcher posts contained "?" and none had a curiosity-gap phrase (5 of 1,428 eligible posts overall). H4c may well end `insufficient`; that is a result, and the data is not widened to avoid it.
- **Prerequisites:** milestone 1 roster; `framing` at Cohen's kappa ≥ 0.7 (plan decision 30); self-reply counts from the collected replies (plan decision 16).
- **Threats:**
  - Replies are counted, not read. A question may draw social replies, not technical ones, and H4a cannot tell them apart.
  - Thread openers carry the author's own replies; these are subtracted.
  - An author's questions may be on different topics from their claims. Rigor and archetype mix per arm are reported.

AGENTS.md §7 rules out recommending curiosity-gap hooks. Whatever H4c shows is reported as a finding and never becomes a template.

## Amendments

## Runs

- 2026-11-12, `dry_run` on v0 (rule-proxy framing, 38–49 posts, 0–1 strata): harness check only; see ledger and daily log. Not evidence.

## Verdict
