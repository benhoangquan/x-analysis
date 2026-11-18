# Experiments

Hypothesis tests for the claims in [../10_project_doc.md](../10_project_doc.md). The loop borrows from Karpathy's autoresearch: a fixed evaluation harness, a baseline run before the real one, one ledger row per run whatever the outcome, and a simplicity bar on methods. Two changes fit observational data. The plan and its decision rule are frozen in git before any outcome is seen (pre-registration), and a run records a verdict rather than keeping or discarding a change.

## Index

| ID | Tests | Data | New inputs | Status |
|---|---|---|---|---|
| [E1](E1_poster_role.md) | H1: reach vs intent by poster credentials | paper panel | `poster_role` label | done |
| [E2](E2_paper_matched_levers.md) | H2: figure plus contested claim, same paper | paper panel | summary class from the taxonomy revision | done |
| [E3](E3_decision_model.md) | H3: controllable features predict top-half posts | paper-linked posts | paper metadata, scikit-learn | done |
| [E4](E4_framing.md) | H4: question vs claim vs curiosity gap | roster | `framing` label | done |
| [E5](E5_variance_shares.md) | Open question 1: variance share of five factors | paper panel | E1–E3 inputs | done, exploratory |
| [E6](E6_reply_vs_bookmark_language.md) | Open question 2: reply vs bookmark language | roster | rule features | done, exploratory |
| [E7](E7_small_account_breakout.md) | H5: small-account breakout vs polarization | roster + panel (`<2,500`) | Quote-to-Retweet ratio, sub-tiers | done |

Status values: `draft` → `frozen` (pre-registration committed after Ben approves) → `running` → `done`.

Shared definitions: [paper panel](../30_concepts/paper_panel.md), [poster role](../30_concepts/poster_role.md), [framing](../30_concepts/framing.md), [intent measures](../30_concepts/intent_measures.md).

## Order

1. **Before new data:** build the stratified estimator and the negative control, then dry-run each experiment on v0. Dry runs check code only; their status is `dry_run` and they are never evidence.
2. **Data:** milestone 1, plus the paper panel's first batch of 30 papers, which checks the `url:` search and the number of posters per paper.
3. **Labels:** milestone 3, with `poster_role` and `framing` added to the hand-label set.
4. **Freeze E1–E4 and E7.** Counting arms and strata is allowed before freezing; outcomes are not looked at. A feasibility gate that fails changes the primary test before the freeze, as each file states.
5. **Run:** E6, E4 and E7 (roster/small accounts), then E1 and E2 (panel), then E3, then E5.
6. **Causal test:** levers supported by E2 and E4 become the template arm of the posting experiment (plan milestone 5). Everything before it is association.

## The loop

For each experiment:

1. **Pre-register.** Complete the Pre-registration section. After Ben approves, commit it with the message `exp: freeze E<n>` and set the status to `frozen (commit <hash>, YYYY-MM-DD)`. From then on the section is read-only; any change before the real run goes in a dated Amendments entry with its reason.
2. **Negative control.** Run the primary tests with arm labels shuffled within strata (seed recorded). The rate ratio should sit near 1 with an interval covering 1. If it does not, the harness is broken: log `error`, fix, and rerun the control.
3. **Run.** `uv run python -m src.analysis.experiments <E#> > outputs/runs/<E#>_<YYYY-MM-DD>.log 2>&1`. The script ends with a summary block of `key: value` lines. Numbers in the notes are copied from that block.
4. **Record.** One ledger row per test in [results.tsv](results.tsv), a dated entry in the experiment's Runs section, and a `[RUN]` entry in the daily log.
5. **Conclude.** Write the Verdict section, set the status to `done`, and update the hypothesis row and Key findings in the project doc.
6. **Rerun** only for a new data version, a new label version or a bug fix, named in the row's description. A rerun adds rows; earlier rows stay.

Once an experiment is frozen, go through steps 2–5 without pausing. Ask Ben first before spending on Apify or Jev beyond the plan's estimates, changing the harness, amending a frozen pre-registration, or rewording a hypothesis.

## Fixed harness

An experiment uses these as they are:

- metric formulas (`src/metrics/formulas.py`); eligibility, maturity, per-author cap and shrinkage (`src/metrics/baselines.py`);
- the researcher filter and the label rubric at the frozen `label_version`;
- the estimator, evidence gate and verdict rule below.

Changing any of them is a decision (project doc and plan). It bumps the relevant version, and every ledger row that depended on it is rerun.

## Estimator: stratified rate ratio

Every comparison of two arms A and B is a Mantel–Haenszel rate ratio over strata s. The strata hold constant what the hypothesis says to hold constant: a paper, an author, or a follower tier.

```text
RR = Σ_s (c_As · e_Bs / e_s) / Σ_s (c_Bs · e_As / e_s),   e_s = e_As + e_Bs
```

`c` is the count (bookmarks, other people's replies, or the weighted interactions of `S_intent`) and `e` the exposure (impressions; likes for bookmarks per like). Only strata holding both arms contribute. When one arm has zero total count across all contributing strata while the other arm is positive, a Haldane `+0.5` continuity adjustment is applied across contributing strata so zero-count arms (e.g., zero bookmarks in H5) stay finite. Interval: percentile bootstrap with 2,000 resamples of the cluster unit (papers for paper strata, authors otherwise).

Simplicity bar: a method more complex than this is used only where this one cannot answer the question (E3, E5), and the pre-registration says why. At equal results, the simpler method is the one reported.

## Evidence gate

A test gets a verdict only with at least 20 posts per arm, 10 distinct authors per arm and 20 contributing strata. Otherwise its verdict is `insufficient`. This is the plan's minimum evidence plus a strata count. Exceptions: E1's cross-paper tests need 5 contributing strata (plan decision 50), and E7's sub-tier tests need 2 contributing strata across the 3 sub-tiers within `<2,500` followers (plan decision 61).

## Verdict rule

H1–H5 have eleven primary tests between them (E1 three, E2 one, E3 one, E4 three, E7 three), so verdicts use 99% intervals; 95% intervals are reported alongside. The smallest effect worth changing how Martin writes is a rate ratio of 1.2 (0.83 in the other direction).

| Verdict | Directional prediction (RR > 1) | Null prediction ("no lift") |
|---|---|---|
| `supported` | lower bound > 1 | upper bound < 1.2 |
| `refuted` | upper bound < 1, or whole interval inside [0.83, 1.2] | lower bound > 1 |
| `inconclusive` | anything else | anything else |

A supported test whose upper bound is below 1.2 is reported as "supported, small". With these sample sizes, `inconclusive` means "no large effect detected", never "no effect".

Other ledger statuses: `insufficient` (evidence gate failed), `exploratory` (E5, E6 discovery), `control` (negative control passed), `dry_run` (v0 or synthetic data), `error` (crash, or negative control failed).

## Ledger

[results.tsv](results.tsv) is tab-separated, one row per test per run, and append-only.

| Column | Content |
|---|---|
| `date` | YYYY-MM-DD |
| `commit` | 7-character hash of the code that ran, from a clean tree |
| `exp` | E1–E6 |
| `test` | H1a, H1b-O, H4c, NC (negative control), … |
| `data_version` | collection snapshot, e.g. `v0-2026-11-11` |
| `label_version` | label hash, or `-` |
| `estimate` | rate ratio (ΔAUC for E3, share for E5) |
| `ci_low`, `ci_high` | 99% interval |
| `n_posts`, `n_authors`, `n_strata` | sample sizes after the gate |
| `status` | verdict or run status (above) |
| `description` | one line: what ran and why |

## Experiment file template

```markdown
# E<n>: <title>

Status: draft
Tests: H<n> (wording in the project doc)

## Pre-registration
- **Data:**
- **Arms:**
- **Strata:**
- **Primary tests:** count, exposure, comparison, prediction
- **Secondary:**
- **Decision:**
- **Feasibility gate:**
- **Prerequisites:**
- **Threats:**

## Amendments
## Runs
## Verdict
```
