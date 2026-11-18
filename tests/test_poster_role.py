from src.enrichment.poster_role import (
    CREDENTIALED,
    NON,
    ORIGINAL,
    build_request,
    decide,
    parse,
)


def test_truth_table_precedence():
    assert decide(True, 0.1, 0.1) == ORIGINAL  # name on the author list
    assert decide(False, 0.9, None) == ORIGINAL  # "our paper"
    assert decide(False, 0.2, 0.85) == CREDENTIALED  # research role in the bio
    assert decide(False, 0.2, 0.1, s2_papers=3) == CREDENTIALED
    assert decide(False, 0.2, 0.1, s2_papers=2) == NON
    assert decide(False, 0.79, 0.79) == NON  # both just under the cutoff


def test_request_and_parse():
    body = build_request("New paper!", "Ada Lovelace", "", "OpenART", "Ada Lovelace; A. Turing",
                         "jev-latest")  # fmt: skip
    assert "bio" not in body["state"] and set(body["questions"]) == {"own_work"}
    out = parse({"own_work": {"noul": 0.2}}, "Ada Lovelace", "Ada Lovelace; Alan Turing")
    assert out["name_match"] and out["poster_role"] == ORIGINAL


def test_parse_with_s2_papers_and_s2_helpers(tmp_path):
    from src.enrichment.s2 import author_ml_paper_count, fetch_paper_s2_meta

    out = parse({"own_work": {"noul": 0.1}, "bio": {"noul": 0.2}}, "Ben", "Other", s2_papers=3)
    assert out["s2_papers"] == 3 and out["poster_role"] == CREDENTIALED

    # Single-word handles skip S2 lookup completely
    called = []
    assert author_ml_paper_count("karpathy", fetch_json=lambda u: called.append(u) or {}) == 0
    assert not called

    fake_s2 = {
        "data": [
            {
                "name": "Ada Lovelace",
                "papers": [
                    {"externalIds": {"ArXiv": "2608.00001"}},
                    {"externalIds": {"ArXiv": "2608.00002"}},
                    {"externalIds": {"ArXiv": "2608.00003"}},
                    {"externalIds": {"ArXiv": "2608.00004"}},
                ],
            },
            {
                "name": "Ada Other",
                "papers": [{"externalIds": {"ArXiv": "2608.00001"}}],
            },
        ]
    }
    cats = {
        "2608.00001": {"cs.LG"},
        "2608.00002": {"cs.CL"},
        "2608.00003": {"stat.ML"},
        "2608.00004": {"physics.gen-ph"},
    }
    n = author_ml_paper_count(
        "Ada Lovelace",
        fetch_json=lambda _u: fake_s2,
        fetch_arxiv=lambda _ids: cats,
        cache_dir=tmp_path / "s2_au",
    )
    assert n == 3

    def fake_post(_url, payload):
        assert payload["ids"] == ["ARXIV:2608.00001", "ARXIV:2608.00002"]
        return [
            {
                "venue": "ICLR",
                "publicationVenue": {"name": "ICLR", "type": "conference"},
                "authors": [{"name": "A", "hIndex": 10}, {"name": "B", "hIndex": 30}],
            },
            {
                "venue": "arXiv.org",
                "publicationVenue": {"name": "arXiv.org", "type": "preprint"},
                "authors": [{"name": "C", "hIndex": 5}],
            },
        ]

    meta = fetch_paper_s2_meta(
        ["2608.00001", "2608.00002"],
        post_json=fake_post,
        cache_dir=tmp_path / "s2_p",
    ).set_index("paper_id")
    assert bool(meta.loc["2608.00001", "venue_accepted"]) is True
    assert bool(meta.loc["2608.00002", "venue_accepted"]) is False
    assert meta.loc["2608.00001", "max_h_index"] == 30.0
    assert meta.loc["2608.00001", "median_h_index"] == 20.0
