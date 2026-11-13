# Poster role

Status: accepted 2026-11-12 (plan decision 30). Used by E1, E3, E5.

How the account posting about a paper relates to that paper. One label per post that links a paper. H1 calls this "poster tier"; it is renamed so that "tier" keeps meaning follower tier.

| Role | Definition | Signals |
|---|---|---|
| `PAPER_AUTHOR` | The poster wrote the paper, or is the official account of the authors' lab. | display name on the arXiv author list; "our paper", "we show" |
| `HYPE_EXPLAINER` | Not an author. Frames the paper with claims beyond what it reports, to draw a general audience. | "changes everything", "RIP <method>", emoji stacks, curiosity gaps, `hype_flags` |
| `COMMENTATOR` | Not an author. Adds a judgment of their own (critique, agreement, context) without hype. | "not convinced by the baselines", "matches what we saw" |
| `NEUTRAL_CURATOR` | Not an author. Reports what the paper does, in the paper's own terms. | title, short summary, a figure |

Precedence when several fit: `PAPER_AUTHOR` > `HYPE_EXPLAINER` > `COMMENTATOR` > `NEUTRAL_CURATOR`.

**Labelling.** `PAPER_AUTHOR` when the account's display name matches a name on the arXiv author list (normalised), or when Jev says the post presents the work as the poster's own with probability ≥ 0.8. The other three come from one Jev question on text and images.

**Validation.** Ben labels 100 paper-linked posts (25 per Jev role) blind to Jev; target Cohen's kappa ≥ 0.7. 50 name matches are checked by hand.

**Account role.** The role of at least 60% of an account's paper-linked posts; otherwise `MIXED`. Used in secondary analyses only.
