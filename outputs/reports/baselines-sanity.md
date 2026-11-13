# Baselines sanity check

Reach model: log(views) = intercept + slope * log(max(followers, 100)). Fit: slope 0.27, intercept 8.40 on
1428 posts from 810 authors. Status: **reliable**.
Posts with a trailing-30-day baseline (>=3 prior eligible posts, OWN/BENCHMARK): 312 posts across 10 authors.

## Per follower tier (eligible, mature posts)

| follower_tier | posts | authors | median_views | median_r_out | median_reach_vs_expected | median_s_intent | median_cr_bmk |
|---|---|---|---|---|---|---|---|
| <2k | 123 | 94 | 33,472 | 52.0 | 1.50 | 0.0279 | 1.91 |
| 2k-20k | 388 | 263 | 75,050 | 9.0 | 1.55 | 0.0376 | 3.00 |
| 20k-200k | 458 | 283 | 96,894 | 1.5 | 1.09 | 0.0283 | 2.72 |
| >200k | 459 | 170 | 103,533 | 0.1 | 0.62 | 0.0194 | 1.60 |

Review checklist: reach_vs_expected medians near 1.0 within each tier; the fit slope below 1
(views grow slower than followers); tiers with one author are not comparable to each other.
