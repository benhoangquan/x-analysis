# E6: Language of reply-leaning vs bookmark-leaning posts

Status: draft (exploratory, with a confirmation half)
Answers: open question 2 in the project doc.

## Pre-registration

- **Data:** `ROSTER` posts that are filter-passing, eligible, mature and inside the author cap.
- **Lean:** within each follower tier, compute the shrunk rate of other people's replies and `cr_bmk_shrunk`. Reply-leaning: top quartile for replies and below the median for bookmarks. Bookmark-leaning: top quartile for bookmarks and below the median for replies. Other posts are left out.
- **Features (fixed list, rule-coded):** direct question; "do you know" or "did you know"; curiosity-gap lexicon; first person singular; first person plural; second person; third-person paper framing ("the authors", "this paper"); imperative opener; hedges; numbers; emoji; length tercile; link; thread; venue mention.
- **Split:** authors are split 50/50 at random. The seed goes in Amendments before the run.
- **Discovery half:** log odds ratio of each feature in reply-leaning vs bookmark-leaning posts, with a 95% author-bootstrap interval. Shortlist: up to 5 features whose interval excludes 0, largest effect first.
- **Confirmation half:** only the shortlist is tested. A pattern is confirmed when its log odds ratio has the same sign and a 99% interval excluding 0.
- **Output:** confirmed patterns go to the project doc as candidate hypotheses (H5 onward) for Ben to word. Unconfirmed ones are logged as discovery-only.
- **Prerequisites:** milestone 1; researcher filter at target. E6 needs rule features only, so it can run first.
- **Threats:** shrinkage toward tier rates compresses small accounts; quartiles are computed within tier for that reason. Replies are counted, not read.

## Amendments

- 2026-11-17 (before freeze): `SEED = 20261112` recorded for the 50/50 author discovery/confirmation split; Milestone 3 manual hand-labelling waived under plan decision 60 (`label_version=cf3607061e63`). Outcome-blind `v1-2026-11-17` input slice (`ROSTER` filter-passing, eligible, mature, `in_author_cap`): `1,537` posts across `191` authors.

## Runs

- 2026-11-12, `dry_run` on v0 (9 leaning posts from 9 authors): pipeline runs end to end; no result. See ledger.

## Result
