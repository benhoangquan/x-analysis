# Paper panel

Status: accepted 2026-11-12 (plan decision 29). Used by E1, E2, E3, E5.

A sample of arXiv papers together with every post that links them, so posts about the same paper can be compared.

**Why.** Timelines of a fixed roster rarely overlap on a paper. In v0, 142 of 145 linked arXiv papers had one poster, 3 had two and none had more (daily log 2026-11-12).

**Build.**

1. Seeds: arXiv IDs linked from `ROSTER` posts in the window, read from expanded URLs (arxiv.org abs/pdf/html, huggingface.co/papers, alphaxiv.org).
2. Draw 300 IDs uniformly at random within each month, never by engagement.
3. Collect posts that link each ID within 30 days of its first version: `(url:"arxiv.org/abs/<id>" OR url:"huggingface.co/papers/<id>" OR …) -filter:retweets`, with IDs grouped so each query expects at least 50 posts.
4. Posts from accounts outside the roster get cohort `PANEL`. Every paper-linked post gets a `paper_id`.
5. Paper metadata: arXiv API (categories, first-version date, authors, code link) and Semantic Scholar (author h-index, venue).

**Analysis set.** Papers with at least 3 distinct posters.

**First batch (30 papers) checks:**

- whether `url:` matches IDs inside expanded links (10 posts checked against X);
- the median number of posters per paper. Below 3, seeds are drawn from papers with at least 2 roster posters, or from Hugging Face daily papers, and the scope note below changes.

**Cost.** About 300 papers × 15 posts ≈ 4,500 posts ≈ $2.

**Scope.** Results describe papers that researchers share, not arXiv at large.
