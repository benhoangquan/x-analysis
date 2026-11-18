# Corpus summary & baselines (8660 posts)

Window: 2026-08-09 to 2026-11-06 (collected 2026-11-17; 407 authors).

**Descriptive only.** Hypothesis verdicts and evidence-gated templates come from Milestone 4 (`experiments.py`, `lift.py`, `report.py`) once Jev labels are attached.

## Funnel

| stage | posts |
|---|---|
| rows loaded | 8660 |
| eligible (no replies/retweets) | 8660 |
| mature (>=7 days) | 8660 |
| within author cap (<=40/author) | 2870 |

## Cohort × follower tier (all loaded posts)

| cohort | follower_tier | posts | eligible | mature | authors | median_views | median_cr_bmk | median_cr_bmk_shrunk |
|---|---|---|---|---|---|---|---|---|
| BENCHMARK | 2k-20k | 5 | 5 | 5 | 1 | 917 | 0.57 | 1.83 |
| BENCHMARK | 20k-200k | 9 | 9 | 9 | 1 | 13,326 | 0.65 | 1.09 |
| BENCHMARK | >200k | 18 | 18 | 18 | 1 | 52,892 | 1.87 | 1.93 |
| OWN | <2k | 27 | 27 | 27 | 2 | 234 | 0.00 | 3.07 |
| PANEL | <2k | 142 | 142 | 142 | 117 | 341 | 1.71 | 3.40 |
| PANEL | 2k-20k | 100 | 100 | 100 | 72 | 1,518 | 5.51 | 4.30 |
| PANEL | 20k-200k | 43 | 43 | 43 | 20 | 1,095 | 5.52 | 3.90 |
| PANEL | >200k | 1 | 1 | 1 | 1 | 8,967 | 8.81 | 8.46 |
| ROSTER | <2k | 1245 | 1245 | 1245 | 122 | 306 | 0.34 | 3.27 |
| ROSTER | 2k-20k | 4395 | 4395 | 4395 | 48 | 890 | 3.02 | 3.29 |
| ROSTER | 20k-200k | 2472 | 2472 | 2472 | 17 | 6,191 | 1.37 | 2.62 |
| ROSTER | >200k | 203 | 203 | 203 | 5 | 25,733 | 3.04 | 3.14 |

## Rule features vs intent (eligible, mature posts; descriptive)

| feature | value | n | authors | median_s_intent | median_cr_bmk |
|---|---|---|---|---|---|
| has_media | False | 4029 | 277 | 0.0180 | 1.03 |
| has_media | True | 4631 | 250 | 0.0297 | 3.80 |
| has_link | False | 2809 | 125 | 0.0169 | 1.03 |
| has_link | True | 5851 | 404 | 0.0293 | 3.51 |
| has_number | False | 2112 | 138 | 0.0163 | 0.85 |
| has_number | True | 6548 | 394 | 0.0269 | 3.04 |
| is_question | False | 7744 | 366 | 0.0239 | 2.10 |
| is_question | True | 916 | 164 | 0.0216 | 1.76 |
| is_thread_opener | False | 8572 | 390 | 0.0236 | 2.03 |
| is_thread_opener | True | 88 | 59 | 0.0332 | 3.97 |

## Tiptree's own posts (eligible, mature)

| author_handle | text | followers_at_collection | impressions | r_out | s_intent | cr_bmk | cr_bmk_shrunk | media_count |
|---|---|---|---|---|---|---|---|---|
| martincsweiss1 | Most of my papers are borderline, because I like writing papers slight | 234 | 9,429 | 40.3 | 0.0299 | 6.58 | 6.29 | 1 |
| martincsweiss1 | Playing an infinite game well means looking silly to people. Most of y | 234 | 74 | 0.3 | 0.0541 | 13.51 | 4.26 | 0 |
| martincsweiss1 | My main contribution to the most-cited paper with my name on it is a s | 234 | 461 | 2.0 | 0.0325 | 4.34 | 3.81 | 1 |
| martincsweiss1 | bf16 might be freezing your weight updates! If you fine-tune in bf16,  | 234 | 272 | 1.2 | 0.0588 | 3.68 | 3.59 | 1 |
| tiptreesystems | Excited to announce that @Lacuna_Research is now listed in Claude's co | 69 | 298 | 3.0 | 0.0268 | 3.36 | 3.52 | 1 |
| martincsweiss1 | I’ve decided to take X more seriously. https://t.co/HQYnUuf3D6 | 234 | 63 | 0.3 | 0.0476 | 0.00 | 3.36 | 1 |
| tiptreesystems | How compositional is an object? Can you put a number to it? Today's pa | 69 | 70 | 0.7 | 0.0143 | 0.00 | 3.34 | 0 |
| tiptreesystems | Would you publish at a venue that required you to submit code with you | 69 | 74 | 0.7 | 0.0135 | 0.00 | 3.33 | 0 |
| tiptreesystems | Know what has been done. Do what hasn't. That's the line on our homepa | 69 | 80 | 0.8 | 0.0375 | 0.00 | 3.31 | 0 |
| tiptreesystems | We hosted the 5th edition of the Multi-Agent Systems and Scientific Di | 69 | 81 | 0.8 | 0.0247 | 0.00 | 3.30 | 1 |
| martincsweiss1 | This is a fun learning tool. It helps you find ML research papers loca | 234 | 82 | 0.4 | 0.0000 | 0.00 | 3.30 | 0 |
| martincsweiss1 | Gemini right before it SOTA's felonybench https://t.co/rgq6kfziJK | 234 | 101 | 0.4 | 0.0297 | 0.00 | 3.24 | 1 |
| martincsweiss1 | I think the best researchers create unique workflows. Everyone thinks  | 234 | 158 | 0.7 | 0.0316 | 0.00 | 3.08 | 0 |
| tiptreesystems | It's been a good day on the front page of HN for our company's first N | 69 | 163 | 1.6 | 0.0184 | 0.00 | 3.07 | 0 |
| martincsweiss1 | I often give this advice to students, so I thought I'd create an artif | 234 | 165 | 0.7 | 0.0303 | 0.00 | 3.07 | 1 |
| martincsweiss1 | Here’s Claude using Lacuna MCP to trace the FlashAttention repo to its | 234 | 175 | 0.7 | 0.0171 | 0.00 | 3.04 | 1 |
| martincsweiss1 | Another piece of advice I've been giving to students: make sure the la | 234 | 532 | 2.3 | 0.0188 | 1.88 | 2.98 | 1 |
| martincsweiss1 | The first #NeurIPS2026 Main Track paper from my @IVADO_Qc Postdoc Entr | 234 | 221 | 0.9 | 0.0498 | 0.00 | 2.93 | 0 |
| martincsweiss1 | HackerNews has a second-chance pool, a mechanism where new submissions | 234 | 234 | 1.0 | 0.0513 | 0.00 | 2.89 | 1 |
| martincsweiss1 | I spoke with @muradhem at @globeandmail about Ottawa’s investment in @ | 234 | 237 | 1.0 | 0.0422 | 0.00 | 2.89 | 0 |
| martincsweiss1 | Our traffic to @Lacuna_Research has been hockey-sticking. Considering  | 234 | 250 | 1.1 | 0.0320 | 0.00 | 2.86 | 1 |
| martincsweiss1 | I wrote an essay called AI Science vs. Human Science. I was inspired b | 234 | 1,442 | 6.2 | 0.0277 | 2.08 | 2.69 | 1 |
| martincsweiss1 | When I read papers for a literature review, I want my notes to still b | 234 | 1,610 | 6.9 | 0.0143 | 1.86 | 2.52 | 1 |
| tiptreesystems | Here’s how we figured out our AEO: 1. we made the site really fast - m | 69 | 537 | 5.4 | 0.0186 | 0.00 | 2.32 | 1 |
| martincsweiss1 | Each dot a coding agent search from the last 7 days on our ML research | 234 | 2,506 | 10.7 | 0.0200 | 1.60 | 2.16 | 1 |
| martincsweiss1 | I work with Claude to do research all day. I very frequently ask it to | 234 | 664 | 2.8 | 0.0166 | 0.00 | 2.15 | 0 |
| tiptreesystems | Save machine-learning papers in Lacuna and talk them through with Alth | 69 | 5,044 | 50.4 | 0.0018 | 0.20 | 0.76 | 1 |
