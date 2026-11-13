# Notes protocol

`notes/` is the project's lab notebook. It holds what was seen, run, found and decided, so any session, human or agent, starts from the recorded state instead of from memory.

## Layout

| Path | Holds | How it changes |
|---|---|---|
| `00_daily_log/YYYY-MM-DD.md` | Everything that happened that day, in order | append-only |
| `10_project_doc.md` | Current state: hypotheses, open questions, key findings, decisions | rewritten in place so it stays true |
| `20_literature/<slug>.md` | One source per file (paper, post, blog, docs page) | edited |
| `30_concepts/<slug>.md` | One defined term per file | edited; a changed definition is a decision |
| `40_experiments/E<n>_<slug>.md` | One experiment: pre-registration, amendments, runs, verdict | pre-registration frozen once committed; runs append-only |
| `40_experiments/results.tsv` | The ledger: one row per test per run | append-only |

How experiments run is in [40_experiments/README.md](40_experiments/README.md).

## Session steps

1. **Start.** Read `10_project_doc.md` (Current state first), the latest daily log, and the file of any experiment you will touch.
2. **Work.** Append an entry to today's daily log as each thing happens. Create the file if it is the day's first entry.
3. **End.** Rewrite the Current state section of the project doc. Update every hypothesis status, finding, open question and decision the session changed. The session is done when someone reading only the project doc and today's log would know what changed and what comes next.

## Daily log entries

One heading per entry, tagged with its kind, in the order things happened:

```markdown
### [OBS] Only 3 of 145 arXiv papers in v0 have more than one poster
Source: count over data/raw/*.jsonl (v0-2026-11-11, 2,073 posts).
So what: H2 needs a paper-matched collection. → E2, plan decision 29.
```

| Tag | Use for | Must carry |
|---|---|---|
| `[OBS]` | Something seen in data, code or a source | source and data version |
| `[RUN]` | An experiment or analysis run | experiment ID, ledger status, log path |
| `[FIND]` | A verdict or confirmed result | the ledger row it rests on |
| `[DEC]` | A decision made or proposed | who decided, and where it is recorded |
| `[Q]` | A new question | where it is tracked (project doc, plan item) |
| `[BLOCK]` | Something stopping work | what unblocks it, and who |
| `[NEXT]` | Hand-off for the next session | concrete actions |

`[FIND]` always cites a ledger row; a result without one is an `[OBS]`.

## Rules

- **Append-only logs.** Correct a past entry with a new entry that cites it. Past daily logs and ledger rows stay as written.
- **One home per fact.** Method rules live in the plan and AGENTS.md; definitions in `30_concepts/`; numbers in the ledger; experiment designs in `40_experiments/`. Other notes link to the home.
- **Name the evidence.** Every number names its data version and label version. v0 numbers (`v0-2026-11-11`) show feasibility only and never count as evidence for a hypothesis.
- **Absolute dates**, as YYYY-MM-DD.
- **Hypothesis wording is Ben's.** Propose a rewording or a new hypothesis as an `[DEC]` entry and in the project doc's open questions; Ben changes the wording.
- **Decisions in two tiers.** A decision that changes collection, metrics, labels or outputs goes in the plan's decision table (and AGENTS.md when it changes a rule there), with a one-line pointer in the project doc. Research decisions (scope, experiment design) live in the project doc's Decisions table.

## Project doc sections

1. **Current state:** as-of date, phase, what blocks the hypothesis tests, next three actions.
2. **Hypotheses:** one status row per hypothesis, then the statements in Ben's wording, each with a "Measured as" line.
3. **Open questions:** each with where it is answered (an experiment or a plan item).
4. **Key findings:** verdicts only, each with its ledger row and data version.
5. **Decisions:** ID, date, decision, status (`proposed` or `accepted`), where it is recorded.

Hypothesis status values: `untested`, `testing`, `supported`, `refuted`, `inconclusive`, `insufficient`, `mixed` (sub-tests disagree; list them).

## Literature and concept notes

A literature note starts with the citation and link, then what the source claims, the evidence behind it, and which hypothesis or decision it bears on. A concept note starts with a status line (`proposed` or `accepted`, with the plan item) and the experiments that use it, then the definition and how it is labelled or measured.
