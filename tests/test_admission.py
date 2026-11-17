from src.ingestion.admission import ADMIT, BORDERLINE, REJECT, build_request, decide, parse


def test_truth_table():
    assert decide(0.9, [0.8]) == ADMIT  # research bio and a research post
    assert decide(0.1, [0.8, 0.9]) == ADMIT  # posts carry it without a bio
    assert decide(None, [0.75, 0.8]) == ADMIT
    assert decide(0.9, [0.2]) == REJECT  # research bio, but nothing for researchers
    assert decide(0.1, [0.5, 0.6]) == REJECT  # no research bio and no strong post
    assert decide(0.1, [0.9]) == BORDERLINE  # one strong post, no bio support
    assert decide(0.5, [0.5]) == BORDERLINE
    assert decide(0.9, []) == BORDERLINE


def test_request_leaves_out_empty_bio_and_caps_posts():
    r = build_request("Ada", "", ["a", "b", "c", "d"], "jev-latest")
    assert "bio" not in r["state"] and "bio" not in r["questions"]
    assert list(r["state"]["posts"]) == ["post_1", "post_2", "post_3"]
    assert {"org", "aud_post_1", "aud_post_3"} <= set(r["questions"])


def test_parse():
    out = parse({"bio": {"noul": 0.9}, "aud_post_1": {"noul": 0.8}, "org": {"noul": 0.1}})
    assert out["decision"] == ADMIT and out["p_posts"] == "0.80"


def test_review_sheet_is_blind_and_balanced(tmp_path):
    import pandas as pd

    from src.ingestion.roster import review_sheet

    n = 120
    cands = pd.DataFrame({"handle": [f"h{i}" for i in range(n)], "name": "x", "tier": "<2k",
                          "followers": 10, "bio": "b", "post_1": "p", "post_2": "",
                          "post_3": ""})  # fmt: skip
    dec = ["admit"] * 70 + ["reject"] * 40 + ["borderline"] * 10
    adm = pd.DataFrame({"handle": cands["handle"], "decision": dec, "p_bio_research": 0.5,
                        "p_posts": "0.5", "p_org": 0.1})  # fmt: skip
    sheet = review_sheet(cands, adm, key_path=tmp_path / "key.csv")
    key = pd.read_csv(tmp_path / "key.csv")
    assert len(sheet) == 75 and (key["decision"] == "admit").sum() == 50
    assert not {"decision", "p_bio_research", "p_posts", "sources"} & set(sheet.columns)
    assert list(sheet["handle"]) == list(key["handle"])
