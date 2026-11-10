# Baselines sanity check

Reach model: log(views) = intercept + slope * log(max(followers, 100)). Fit: slope 0.87, intercept 1.57 on
18 posts from 4 authors. Status: **NOT reliable (below the 20 posts / 10 authors gate)**.
Posts with a trailing-30-day baseline (>=3 prior eligible posts, OWN/BENCHMARK): 5 posts across 2 authors.

## Per follower tier (eligible, mature posts)

| follower_tier | posts | authors | median_views | median_r_out | median_reach_vs_expected | median_s_intent | median_cr_bmk |
|---|---|---|---|---|---|---|---|
| <2k | 13 | 2 | 875 | 4.0 | 1.91 | 0.0141 | 0.00 |
| 2k-20k | 2 | 1 | 2,765 | 0.2 | 0.14 | 0.0065 | 0.29 |
| >200k | 3 | 1 | 6,983,217 | 1.6 | 2.36 | 0.0239 | 4.32 |

Review checklist: reach_vs_expected medians near 1.0 within each tier; the fit slope below 1
(views grow slower than followers); tiers with one author are not comparable to each other.
