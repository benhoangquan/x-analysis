# Baselines sanity check

Reach model: log(views) = intercept + slope * log(max(followers, 100)). Fit: slope 0.59, intercept 1.84 on
8315 posts from 192 authors. Status: **reliable**.
Posts with a trailing-30-day baseline (>=3 prior eligible posts, OWN/BENCHMARK/ROSTER): 7811 posts across 108 authors.

## Per follower tier (eligible, mature posts)

| follower_tier | posts | authors | median_views | median_r_out | median_reach_vs_expected | median_s_intent | median_cr_bmk | capped_posts | median_cr_bmk_shrunk |
|---|---|---|---|---|---|---|---|---|---|
| <2k | 1414 | 241 | 306 | 0.7 | 1.29 | 0.0230 | 0.35 | 906 | 3.28 |
| 2k-20k | 4500 | 121 | 903 | 0.1 | 0.77 | 0.0252 | 3.07 | 1,202 | 3.32 |
| 20k-200k | 2524 | 38 | 6,066 | 0.1 | 1.31 | 0.0222 | 1.41 | 602 | 2.65 |
| >200k | 222 | 7 | 29,032 | 0.1 | 2.04 | 0.0194 | 2.89 | 160 | 3.00 |

Review checklist: reach_vs_expected medians near 1.0 within each tier; the fit slope below 1
(views grow slower than followers); tiers with one author are not comparable to each other.
