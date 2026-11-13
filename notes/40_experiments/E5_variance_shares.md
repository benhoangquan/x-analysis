# E5: Variance shares of the five factors

Status: draft (exploratory: no verdict)
Answers: open question 1 in the project doc.

## Pre-registration

- **Question:** when a post about a paper spreads, what share of the variance comes from paper content, paper authors, posting account, post visual and post copy?
- **Data:** panel papers with at least 3 posters; eligible, mature posts. All posts and filter-passing posts are reported separately.
- **Outcomes:** log impressions (reach) and log `cr_bmk_shrunk` (intent), analysed separately, since the two are expected to split differently.
- **Factor blocks:**

  | Block | Features |
  |---|---|
  | paper content | arXiv primary category, code link, venue acceptance, paper age at posting |
  | paper authors | highest and median h-index, author count |
  | posting account | log followers, follower tier, poster role, cohort |
  | visual | `visual_type` |
  | copy | `hook_archetype`, `framing`, `technical_rigor_score`, length, numbers, hype flags, thread length |

- **Method:** Shapley decomposition of out-of-fold R². Ridge regressions on all 32 subsets of the five blocks, 5-fold cross-validation grouped by paper; a block's share is its average marginal gain in R². 95% intervals from 200 paper bootstraps. Beside the block shares, the intraclass correlation of a paper intercept (one-way ANOVA estimator) gives an upper bound for "everything about the paper", measured or not. A simpler method cannot split shared variance between correlated blocks, which is why this one is used.
- **Output:** one table per outcome: block, share of explained variance, interval, and the unexplained share. It goes in Key findings as the answer to open question 1.
- **Prerequisites:** E1 and E3 inputs; milestone 3 labels at target.
- **Threats:**
  - Blocks are correlated (well-known labs have large accounts). Shapley splits shared variance evenly; that is a convention, not a finding.
  - Measured features stand in for the factors. "Paper content" here is metadata, not what the paper says.

## Amendments

## Runs

## Result
