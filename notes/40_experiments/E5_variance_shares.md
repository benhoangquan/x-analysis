# E5: Variance shares of the five factors

Status: done (exploratory)
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

- 2026-11-17 (before freeze): Milestone 3 manual hand-labelling waived under plan decision 60 (`label_version=cf3607061e63`, `role_version=55945d80ebf0`). Outcome-blind feasibility counts on `v1-2026-11-17` papers with `>=3` distinct posters (`SEED = 20261112`): `107` papers, `551` posts, `221` authors unfiltered (`511` posts, `189` authors, `107` papers filter-passing).

## Runs

- 2026-11-17, commit `45e155b`, data `v1-2026-11-17`, labels `cf3607061e63` (`role_version=55945d80ebf0`): `551` posts, `221` authors, `107` papers with `>=3` posters (`200` paper bootstraps). Log: `outputs/runs/E5_2026-11-17.log`.

## Result

| Block | `log_impressions` share [95% paper CI] | `log_cr_bmk_shrunk` share [95% paper CI] |
|---|---|---|
| `posting_account` | `0.5196` [`0.3712`, `1.1647`] | `0.0592` [`0.0343`, `0.2154`] |
| `visual` | `0.0862` [`0.0383`, `0.1712`] | `0.0734` [`0.0248`, `0.1500`] |
| `paper_content` | `-0.0477` [`-0.1505`, `0.0671`] | `-0.0057` [`-0.1024`, `0.1396`] |
| `paper_authors` | `-0.0781` [`-0.4042`, `0.0147`] | `-0.0241` [`-0.4409`, `0.0192`] |
| `copy` | `-0.0105` [`-1.2648`, `0.0829`] | `-0.1516` [`-0.1689`, `0.0550`] |
| `unexplained` (`1 - R²_total`) | `0.5305` | `1.0488` |
| `paper_icc` (upper bound) | `0.0940` | `0.1571` |

- **Reach vs intent split:** Reach (`log_impressions`) is dominated by `posting_account` (`52.0%` of variance) with a smaller positive visual contribution (`8.6%`) and `9.4%` latent paper ICC. Bookmark rate (`log_cr_bmk_shrunk`) has almost no `posting_account` concentration (`5.9%`), a positive `visual` share (`7.3%`, CI strictly positive `[0.025, 0.150]`), and a higher paper-identity upper bound (`paper_icc = 0.157`). Negative out-of-fold Ridge $R^2$ shares on sparse `copy` and `paper_*` metadata reflect finite-sample overfitting rather than signal.
