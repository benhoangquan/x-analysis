import json

from src.config import authors_query, paper_query
from src.ingestion.apify import run
from src.ingestion.filler import matches, parse_query, queries_for, split_filler


def _item(**kw):
    base = {"id": "1", "createdAt": "Wed Oct 14 10:00:00 +0000 2026", "text": "hello",
            "author": {"userName": "Rasbt"}, "isReply": False}  # fmt: skip
    return base | kw


def test_parse_authors_query():
    s = parse_query(authors_query(["rasbt", "srush_nlp"], "2026-10-01", "2026-11-07"))
    assert s.authors == {"rasbt", "srush_nlp"} and s.no_replies and s.no_reposts
    assert str(s.since) == "2026-10-01" and str(s.until) == "2026-11-07" and not s.phrases


def test_author_date_and_reply_rules():
    s = parse_query(authors_query(["rasbt"], "2026-10-01", "2026-11-07"))
    assert matches(_item(), s)
    assert not matches(_item(author={"userName": "spammer"}), s)
    assert not matches(_item(createdAt="Sat Nov 14 05:00:00 +0000 2026"), s)  # after until
    assert not matches(_item(createdAt="Sat Nov 07 05:00:00 +0000 2026"), s)  # until exclusive
    assert not matches(_item(isReply=True), s)


def test_bare_paper_ids_and_phrases():
    s = parse_query(paper_query(["2608.00677"], "2026-08-01", "2026-09-05", bare=True))
    assert s.urls == ("2608.00677",)
    link = {"urls": [{"expanded_url": "https://arxiv.org/abs/2608.00677"}]}
    hit = _item(createdAt="Tue Aug 04 10:00:00 +0000 2026", author={"userName": "x"}, entities=link)
    assert matches(hit, s) and not matches(_item(author={"userName": "x"}), s)
    q = '("our paper" OR "we introduce") url:arxiv.org since:2026-10-01 until:2026-10-05'
    p = parse_query(q)
    assert p.phrases == ("our paper", "we introduce") and p.urls == ("arxiv.org",)
    ok = _item(createdAt="Fri Oct 02 10:00:00 +0000 2026", text="Our paper is out",
               entities={"urls": [{"expanded_url": "https://arxiv.org/abs/2609.1"}]})  # fmt: skip
    assert matches(ok, p) and not matches(ok | {"text": "a paper"}, p)


def test_run_stores_query_and_split_drops_filler(tmp_path):
    q = authors_query(["rasbt"], "2026-10-01", "2026-11-07")
    junk = _item(id="2", author={"userName": "spam"})
    path = run([q], 50, "t", token="x", transport=lambda *a: [_item(), junk],
               out_dir=tmp_path, spend_log=tmp_path / "s.csv")  # fmt: skip
    assert queries_for(path) == [q]
    items = [json.loads(x) for x in path.read_text().splitlines()]
    kept, dropped = split_filler(items, queries_for(path))
    assert [i["id"] for i in kept] == ["1"] and [i["id"] for i in dropped] == ["2"]
