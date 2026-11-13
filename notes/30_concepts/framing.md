# Framing

Status: accepted 2026-11-12 (plan decision 30). Used by E3, E4, E5.

The post's main rhetorical move. One label per post.

| Class | Definition | Example |
|---|---|---|
| `CURIOSITY_GAP` | Withholds the payoff so the reader clicks or expands. | "Do you know why…", "Did you know…", "Here's why…", "Nobody is talking about…" |
| `OPEN_QUESTION` | Asks an open technical question and invites answers; the post leaves it unanswered. | "Why does preference tuning collapse output diversity at small scale?" |
| `DECLARATIVE_EMPIRICAL` | States a specific empirical result: a number, a comparison, a benchmark score or an ablation outcome. | "Rank-8 LoRA matches full fine-tuning on GSM8K within 0.3 points." |
| `DECLARATIVE_OTHER` | Any other statement: announcement, summary, opinion. | "New paper on tokenizer design, link below." |

Precedence when several fit: `CURIOSITY_GAP` > `OPEN_QUESTION` > `DECLARATIVE_EMPIRICAL` > `DECLARATIVE_OTHER`. A rhetorical question that the post answers itself is not `OPEN_QUESTION`.

**Labelling.** Jev on the text. A regex flags curiosity-gap phrases beforehand; the lexicon will live in `src/enrichment/rules.py`.

**Validation.** Added as a fifth field to the 200-post hand-label set; target Cohen's kappa ≥ 0.7 on the held-out half.
