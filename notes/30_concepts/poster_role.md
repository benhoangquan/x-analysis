# Poster role

Status: accepted 2026-11-12 (plan decision 30); classes redefined 2026-11-14 on Ben's clarification. Used by E1, E3, E5.

H1 calls this "poster tier"; the field keeps the name `poster_role` so "tier" stays follower tier. The role is about the poster's credentials in the field, relative to the linked paper. One label per paper-linked post.

| Role | Definition |
|---|---|
| `ORIGINAL_RESEARCHER` | The poster is an author of the linked paper, or the official account of its authors' lab. |
| `CREDENTIALED_RESEARCHER` | Not an author, but has credentials in the field: a publishing record in ML or AI research, or a bio that states a research position (faculty, PhD student, research scientist or engineer). |
| `NON_RESEARCHER` | Neither. Explainers, aggregators and commentators without field credentials. H1 treats this group as its "hype explainers". |

Precedence: `ORIGINAL_RESEARCHER` > `CREDENTIALED_RESEARCHER` > `NON_RESEARCHER`.

**Labelling.**
- `ORIGINAL_RESEARCHER`: the account's display name matches a name on the arXiv author list (normalised), or Jev says the post presents the work as the poster's own with probability >= 0.8.
- `CREDENTIALED_RESEARCHER`: proposed rule, for Ben to confirm: the account matches a Semantic Scholar author with at least 3 papers in cs.LG, cs.CL, cs.CV or stat.ML, or Jev, reading the bio, says the poster holds a research position with probability >= 0.8.
- Everything else is `NON_RESEARCHER`.

**Copy is separate.** Hype in the post itself is measured by `hype_flags` and `framing`, not by role. Within `NON_RESEARCHER`, a secondary analysis in E1 splits hype-flagged from unflagged posts.

**Validation.** Ben labels 100 paper-linked posts (about 33 per Jev class) blind to Jev; target Cohen's kappa >= 0.7. 50 author-name matches are checked by hand.

**Account role.** The role of at least 60% of an account's paper-linked posts; otherwise `MIXED`. Secondary analyses only.
