# Intent measures in the hypotheses

Status: accepted 2026-11-12 (plan decision 28). Used by E1–E6.

The hypotheses name their measures in words. This note maps each phrase onto the metric harness. Formulas live in AGENTS.md §3 (Primary Metrics and Hypothesis-Test Measures).

| Phrase | Measured as |
|---|---|
| "High-Intent Score (bookmarks, quotes, and technical replies)" (H1, H2) | Primary: `CR_bmk`. Secondary: `S_intent`, which also weights likes, retweets and all replies. |
| "technical replies" | Not measured. V0 counts replies and does not read them (plan, Out of scope). |
| "raw impressions and likes" (H1) | `impressions` and `likes` as collected |
| "reply rate" (H4) | Reply rate: other people's replies per 1k views |
| "bookmark-to-like ratio" (H4) | Bookmarks per like (pooled) |
| "high-intent researcher saves" (H4) | `CR_bmk` on filter-passing posts |
| "above-median post performance" (H3) | `top_half` |

`CR_bmk` is primary for H1 and H2 because it is already the project's ranking metric and the closest single count to what they describe.
