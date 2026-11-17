# Paper panel

Status: accepted 2026-11-12 (plan decision 29). Used by E1, E2, E3, E5.

A sample of arXiv papers together with every post that links them, so posts about the same paper can be compared.

**Why.** Timelines of a fixed roster rarely overlap on a paper. In v0, 142 of 145 linked arXiv papers had one poster, 3 had two and none had more (daily log 2026-11-12).

**Build.**

1. Seeds (plan decision 39): papers on Hugging Face daily lists dated 2026-08-09 to 2026-10-07, from the free `huggingface.co/api/daily_papers` endpoint. Papers with at least 2 roster posters are added once the roster is collected.
2. Draw 200 papers uniformly at random from that pool, never by upvotes or engagement.
3. Collect posts that link each ID within 30 days of its first version: `(url:<id1> OR url:<id2> …) since:… until:<7 days back> -filter:retweets -filter:replies`, with IDs grouped so each query expects at least 50 posts and stays under 512 characters. The bare-ID form matched more posts than `url:"arxiv.org/abs/<id>"` in the test batch and covers every host.
4. Posts from accounts outside the roster get cohort `PANEL`. Every paper-linked post gets a `paper_id`.
5. Paper metadata: arXiv API (categories, first-version date, authors, code link) and Semantic Scholar (author h-index, venue).

**Analysis set.** Papers with at least 3 distinct posters.

**Test batch (2026-11-14, 13 random papers):** `url:` matches IDs inside expanded links. Posters per paper had a median of 1 and 3 of 13 papers had 3 or more, so the fallback applies: seeds come from papers with at least 2 roster posters or from Hugging Face daily papers (plan item O), and the scope note below changes with it.

**Cost.** About 200 papers × 15 posts ≈ 3,000 posts ≈ $1.50 (plan decision 36).

**Scope.** Results describe papers that drew community attention (Hugging Face daily lists, and later papers several roster accounts posted), not arXiv at large. Comparisons within a paper are unaffected.
