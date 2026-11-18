import json
from pathlib import Path

import pandas as pd

from src.ingestion.apify import record_spend
from src.ingestion.filler import write_sidecar
from src.ingestion.roster import collect_recent, draw_roster


def _runner(posts_per_account):
    def run(queries, max_items, label, out_dir, spend_log):
        handles = [h for h in queries[0].split() if h.lstrip("(").startswith("from:")]
        n = min(max_items, len(handles) * posts_per_account)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = Path(out_dir) / f"{label}.jsonl"
        h0 = handles[0].lstrip("(").removeprefix("from:")
        items = [{"id": f"{label}-{i}", "createdAt": "Tue Oct 20 10:00:00 +0000 2026",
                  "author": {"userName": h0}, "text": "x"} for i in range(n)]  # fmt: skip
        path.write_text("".join(json.dumps(i) + "\n" for i in items))
        write_sidecar(path, queries, max_items, label)
        record_spend(label, 1, max_items, n, spend_log)
        return path
    return run


def test_recent_collection_splits_capped_groups(tmp_path):
    handles = [f"user{i}" for i in range(20)]
    out = collect_recent(handles, _runner(15), tmp_path / "s.csv", out_dir=tmp_path / "r")
    assert out["accounts_done"] == 20 and out["accounts_left"] == 0 and out["capped"] >= 1


def test_recent_collection_stops_at_its_budget(tmp_path):
    log = tmp_path / "s.csv"
    record_spend("recent_000", 1, 100, 1200, log)  # $0.48 of $0.50
    out = collect_recent(["a", "b"], _runner(5), log, out_dir=tmp_path / "r")
    assert out["runs"] == 0 and out["accounts_left"] == 2


def test_draw_roster_caps_tiers_and_drops_organisations():
    n = 200
    tiers = ["<2k"] * 180 + [">200k"] * 20
    cands = pd.DataFrame({"handle": [f"h{i}" for i in range(n)], "tier": tiers,
                          "followers": "1", "sources": "ownpaper"})  # fmt: skip
    adm = pd.DataFrame({"handle": list(cands["handle"]) + ["h0"],
                        "decision": ["admit"] * n + ["reject"],  # later row wins for h0
                        "p_bio_research": 0.9, "p_posts": "0.9",
                        "p_org": [0.1] * 190 + [0.9] * 10 + [0.1]})  # fmt: skip
    roster = draw_roster(cands, adm)
    sizes = roster.groupby("tier").size()
    assert sizes["<2k"] == 150 and sizes[">200k"] == 10  # 10 organisations left out
    assert "h0" not in set(roster["handle"])


def test_hand_picked_join_whatever_jev_decided():
    cands = pd.DataFrame({"handle": ["a", "b", "seed1"], "tier": "<2k", "followers": "1",
                          "sources": "x"})  # fmt: skip
    adm = pd.DataFrame({"handle": ["a", "b", "seed1"], "decision": ["admit", "reject", "reject"],
                        "p_bio_research": 0.5, "p_posts": "0.5", "p_org": 0.1})  # fmt: skip
    roster = draw_roster(cands, adm, hand_picked=["Seed1"])
    assert set(roster["handle"]) == {"a", "seed1"}
    assert roster.set_index("handle").loc["seed1", "hand_picked"]
    assert not roster.set_index("handle").loc["a", "hand_picked"]


def test_roster_months_newest_first_and_shared_cap(tmp_path):
    from src.ingestion.roster import collect_roster

    log = tmp_path / "s.csv"
    record_spend("roster_old", 1, 100, 12_450, log)  # $4.98: a $0.04 run would pass $5
    out = collect_roster(["a", "b"], _runner(5), log, out_dir=tmp_path / "r")
    assert len(out) == 1 and out[0]["window"].startswith("2026-10-08")  # newest month first
    assert out[0]["runs"] == 0 and out[0]["accounts_left"] == 2  # cap stops it


def test_queried_handles_reads_stored_queries(tmp_path):
    from src.ingestion.roster import queried_handles

    collect_recent(["Ann", "bob"], _runner(3), tmp_path / "s.csv", out_dir=tmp_path / "r")
    assert queried_handles(tmp_path / "r") == {"ann", "bob"}


def test_score_review_bar():
    from src.ingestion.roster import score_review

    key = pd.DataFrame({"handle": [f"h{i}" for i in range(75)],
                        "decision": ["admit"] * 50 + ["reject"] * 25})  # fmt: skip
    yes = ["yes"] * 43 + ["no"] * 7 + ["no"] * 25
    done = pd.DataFrame({"handle": key["handle"], "ben_admit": yes})
    s = score_review(done, key)
    assert s["admits_confirmed"] == 43 and s["passes"] and s["rejects_confirmed"] == 25
    done.loc[0, "ben_admit"] = "no"  # 42 of 50 = 84%
    assert not score_review(done, key)["passes"]
    done.loc[0, "ben_admit"] = ""  # an unfilled row also blocks
    assert not score_review(done, key)["passes"]


def test_finalise_applies_ben_verdicts_but_keeps_hand_picked():
    from src.ingestion.roster import finalise

    draft = pd.DataFrame({"handle": ["a", "b", "seed"], "tier": "<2k", "followers": "1",
                          "sources": "x", "hand_picked": ["False", "False", "True"]})  # fmt: skip
    done = pd.DataFrame({"handle": ["b", "seed", "c"], "ben_admit": ["no", "no", "yes"]})
    cands = pd.DataFrame({"handle": ["a", "b", "c", "seed"], "tier": "2k-20k", "followers": "5",
                          "sources": "x"})  # fmt: skip
    out = finalise(draft, done, cands).set_index("handle")
    assert set(out.index) == {"a", "seed", "c"}  # b dropped, c added, seed kept
    assert out.loc["c", "review"] == "ben_yes" and out.loc["a", "review"] == "not_reviewed"


def test_finalise_from_draft_trust_jev():
    from src.ingestion.roster import finalise_from_draft

    draft = pd.DataFrame({
        "handle": ["b", "a", "seed"],
        "tier": ["<2k", "2k-20k", "<2k"],
        "followers": ["10", "5000", "50"],
        "sources": ["ownpaper", "panel", "seed"],
        "hand_picked": ["False", "False", "True"],
    })
    out = finalise_from_draft(draft)
    assert list(out.columns) == ["handle", "tier", "followers", "hand_picked", "review"]
    assert list(out["handle"]) == ["a", "b", "seed"]
    assert (out["review"] == "jev_trusted").all()
    assert out.set_index("handle").loc["seed", "hand_picked"] == "True"


def test_collect_authors_resumes_skipping_completed_accounts(tmp_path):
    from src.ingestion.roster import Window, collect_authors

    w = Window("2026-10-08", "2026-11-07", 5.0, "roster_", tmp_path / "r", 2.0)
    log = tmp_path / "s.csv"
    first = collect_authors(["u1", "u2"], _runner(3), log, w)
    assert first["accounts_done"] == 2 and first["runs"] == 1
    second = collect_authors(["u1", "u2", "u3"], _runner(3), log, w)
    assert second["runs"] == 1 and second["accounts_done"] == 3 and second["accounts_left"] == 0


def test_cohorts_from_roster_file(tmp_path, monkeypatch):
    from src import config
    from src.schema import Cohort

    f = tmp_path / "roster.csv"
    f.write_text("handle\nAlice\n")
    monkeypatch.setattr(config, "ROSTER_FILE", f)
    config.roster_handles.cache_clear()
    assert config.cohort_for("alice") is Cohort.ROSTER
    assert config.cohort_for("stranger", Cohort.PANEL) is Cohort.PANEL
    config.roster_handles.cache_clear()
