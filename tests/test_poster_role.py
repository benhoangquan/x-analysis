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
