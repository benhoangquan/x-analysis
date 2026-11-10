# MVP findings: initial dataset (47 posts)

Data: first Apify test calls (the only ones returned before the actor's free-plan run limit).
Authors: elicitorg, karpathy, martincsweiss1, tiptreesystems, weights_biases. Collected 2026-11-10.

**Read this first.** 18 scored posts from 4 authors is
far below the plan's evidence gate (>=20 posts and >=10 authors per cell). Everything below is
descriptive. There are no lift estimates, no confidence intervals and no hook-archetype or rigor
labels yet (the classifier is milestone 3). Treat the observations as hypotheses to test, not
findings.

## Funnel

| stage | posts |
|---|---|
| rows loaded | 47 |
| eligible (no replies/retweets) | 21 |
| mature (>=7 days) | 18 |

## Per author (eligible, mature posts)

| author_handle | followers | posts | median_views | median_r_out | median_s_intent | median_cr_bmk |
|---|---|---|---|---|---|---|
| weights_biases | 607 | 6 | 2,529 | 4.2 | 0.0097 | 0.72 |
| tiptreesystems | 67 | 7 | 160 | 1.6 | 0.0187 | 0.00 |
| karpathy | 4,442,300 | 3 | 6,983,217 | 1.6 | 0.0239 | 4.32 |
| elicitorg | 14,260 | 2 | 2,765 | 0.2 | 0.0065 | 0.29 |

## Highest-intent posts (by S_intent)

| author_handle | text | impressions | r_out | s_intent | cr_bmk | media_count |
|---|---|---|---|---|---|---|
| karpathy | We'll be spending a lot more time trying to understand the outputs of language m | 8,192,002 | 1.8 | 0.0397 | 10.10 | 1 |
| tiptreesystems | Know what has been done. Do what hasn't. That's the line on our homepage, and it | 78 | 0.8 | 0.0385 | 0.00 | 0 |
| tiptreesystems | Excited to announce that @Lacuna_Research is now listed in Claude's connector di | 283 | 2.8 | 0.0283 | 3.53 | 1 |
| karpathy | Cool eval. Simply ask an LLM “Land or Water?” and give it a latitude and longitu | 1,608,095 | 0.4 | 0.0239 | 3.08 | 0 |
| karpathy | Dusting off this tweet from April because this gap in shared understanding of LL | 6,983,217 | 1.6 | 0.0223 | 4.32 | 0 |
| tiptreesystems | Here’s how we figured out our AEO: 1. we made the site really fast - median page | 520 | 5.2 | 0.0192 | 0.00 | 1 |
| tiptreesystems | It's been a good day on the front page of HN for our company's first NeurIPS Mai | 160 | 1.6 | 0.0187 | 0.00 | 0 |
| weights_biases | So we Forge now? | 875 | 1.4 | 0.0171 | 0.00 | 0 |

## Rule features vs intent (descriptive only)

| feature | value | n | authors | median_s_intent | median_cr_bmk |
|---|---|---|---|---|---|
| has_media | False | 10 | 4 | 0.0163 | 0.20 |
| has_media | True | 8 | 4 | 0.0102 | 0.72 |
| has_link | False | 11 | 4 | 0.0171 | 0.00 |
| has_link | True | 7 | 3 | 0.0091 | 0.63 |
| has_number | False | 4 | 2 | 0.0147 | 0.00 |
| has_number | True | 14 | 4 | 0.0162 | 0.60 |
| is_question | False | 13 | 4 | 0.0136 | 0.63 |
| is_question | True | 5 | 3 | 0.0154 | 0.00 |

## Tiptree's own posts

| author_handle | text | followers_at_collection | impressions | r_out | s_intent | cr_bmk | media_count |
|---|---|---|---|---|---|---|---|
| tiptreesystems | Know what has been done. Do what hasn't. That's the line on our homepa | 67 | 78 | 0.8 | 0.0385 | 0.00 | 0 |
| tiptreesystems | Excited to announce that @Lacuna_Research is now listed in Claude's co | 67 | 283 | 2.8 | 0.0283 | 3.53 | 1 |
| tiptreesystems | Here’s how we figured out our AEO: 1. we made the site really fast - m | 67 | 520 | 5.2 | 0.0192 | 0.00 | 1 |
| tiptreesystems | It's been a good day on the front page of HN for our company's first N | 67 | 160 | 1.6 | 0.0187 | 0.00 | 0 |
| tiptreesystems | How compositional is an object? Can you put a number to it? Today's pa | 67 | 65 | 0.7 | 0.0154 | 0.00 | 0 |
| tiptreesystems | Would you publish at a venue that required you to submit code with you | 67 | 71 | 0.7 | 0.0141 | 0.00 | 0 |
| tiptreesystems | Save machine-learning papers in Lacuna and talk them through with Alth | 67 | 5,042 | 50.4 | 0.0012 | 0.00 | 1 |

## Hypotheses for Martin to test (from this snapshot; not statistically supported)

1. **Reach is not intent.** Tiptree's biggest post by views (5,042, 50x its follower count) is a
   Lacuna/Althea product post with media, and it has the lowest S_intent of the seven (0.0012)
   and no bookmarks. Next time, track bookmarks per 1k views and not views alone, as AGENTS.md
   already prescribes.
2. **Short, claim-led text posts carry Tiptree's intent.** Its top two by S_intent are plain-text
   posts built on one clear claim ("Know what has been done. Do what hasn't.") and a concrete
   research question. Test two or three more posts of this form against a product post on the
   same topic.
3. **Bookmarks are rare for Tiptree.** Only the Claude-connector announcement (3.5 per 1k views)
   scored; the other six are 0. The strongest bookmark rates in the sample (karpathy 4.3 to 10.1)
   come from posts that carry something to save, such as an interpretability argument with a
   figure. Try a post that carries a reusable artefact (a Lacuna map or a result table) and
   check whether CR_bmk moves.
4. **Do not copy karpathy's absolute numbers.** At 4.4M followers his reach is not comparable
   to a 67-follower account. Use the follower-tier comparisons from milestone 2 once more authors
   are collected.

Open limits: no archetype, rigor or visual labels yet; no reach-vs-expected fit (it needs many
authors); the discovery cohort is empty, so nothing here speaks to researcher posts across X.
