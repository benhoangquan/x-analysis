# Intent measures in the hypotheses

Status: accepted 2026-11-12 (plan decision 28); revised 2026-11-14 on Ben's clarification. Used by E1-E6.

The hypotheses name their measures in words. This note maps each phrase onto the metric harness. Formulas live in AGENTS.md section 3.

| Phrase | Measured as |
|---|---|
| "High-Intent Score" (H1, H2) | Primary: `S_intent` exactly as AGENTS.md and the plan define it: (3 x bookmarks + 2 x (quotes + reposts) + 2 x replies + likes) / max(impressions, 1). Secondary: `CR_bmk`. |
| "technical replies" | Dropped. Replies enter `S_intent` as the plain reply count. |
| "raw impressions and likes" (H1) | `impressions` and `likes` as collected |
| "reply rate" (H4) | Reply rate: replies per 1k views on posts that are not thread openers (plan decision 36) |
| "bookmark-to-like ratio" (H4, H5) | Bookmarks per like (pooled) |
| "high-intent researcher saves" (H4) | `CR_bmk` on filter-passing posts |
| "above-median post performance" (H3) | `top_half` |
| "Quote-to-Retweet ratio" (H5) | Pooled `quotes / reposts` (polarization relative to plain amplification) |
| "high-residual breakout posts" (H5) | `reach_vs_expected > 1.0` (positive residual from log views on log followers) |
| "near-zero bookmarks" (H5) | `CR_bmk` alongside `% of posts with 0 bookmarks` |

In the stratified rate ratio, `S_intent` is the weighted count (the numerator above) over impressions.
