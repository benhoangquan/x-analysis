import pandas as pd
import pytest

from src.enrichment import rubric
from src.enrichment.classify import run
from src.enrichment.evaluate import agreement, cohen_kappa
from src.enrichment.judge import JevError, JevJudge
from src.schema import Framing, HookArchetype, PostLabels, VisualType


def answers(researcher=0.9, rigor=(0.05, 0.05, 0.1, 0.7, 0.1), arch=None, visual=None, base=0):
    arch = arch or {}
    a = {"researcher": {"type": "noul", "noul": researcher}}
    a["rigor"] = {"type": "score", "probabilities": {str(i + base): p for i, p in enumerate(rigor)}}
    for h in rubric.ARCHETYPE_QS:
        a[f"arch_{h.value}"] = {"type": "noul", "noul": arch.get(h.value, 0.05)}
    if visual:
        a["visual"] = {"type": "choice", "choice": visual, "probabilities": {visual: 0.9}}
    return a


def test_request_has_no_image_question_without_image():
    body = rubric.build_request("hello", "jev-latest")
    assert "visual" not in body["questions"] and "arch_VISUAL_MAP" not in body["questions"]
    assert "assets" not in body
    body = rubric.build_request("hello", "jev-latest", "img-1", "AAAA", "png")
    assert body["state"]["attached_image"] == "img-1"
    assert body["assets"]["img-1"]["format"] == "png" and "visual" in body["questions"]


def test_rigor_handles_zero_or_one_based_levels():
    for base in (0, 1):
        lab = rubric.parse_answers("1", "v", answers(base=base), None, False)
        assert lab.technical_rigor_score == 4 and lab.rigor_prob == 0.7


def test_archetype_precedence_and_other():
    near = {"CONTESTED_CLAIM": 0.85, "TECHNICAL_BREAKDOWN": 0.80}
    assert rubric.pick_archetype(near)[0] is HookArchetype.TECHNICAL_BREAKDOWN  # within tie band
    far = {"CONTESTED_CLAIM": 0.9, "TECHNICAL_BREAKDOWN": 0.6}
    assert rubric.pick_archetype(far)[0] is HookArchetype.CONTESTED_CLAIM
    assert rubric.pick_archetype({"CONTESTED_CLAIM": 0.3})[0] is HookArchetype.OTHER


def test_visual_type_rules_and_confidence():
    v = rubric.parse_answers
    assert v("1", "v", answers(), None, False).visual_type is VisualType.NONE
    assert v("1", "v", answers(), "video", False).visual_type is VisualType.VIDEO_DEMO
    lab = v("1", "v", answers(visual="paper_figure"), "photo", True)
    assert lab.visual_type is VisualType.PAPER_FIGURE and lab.visual_source == "jev"
    lab = v("1", "v", answers(), "photo", False)  # image unreadable
    assert lab.visual_type is VisualType.OTHER_IMAGE and lab.label_confidence == 0.0


def test_jev_judge_retries_without_rejected_image():
    calls = []

    def transport(body, headers):
        calls.append(("assets" in body, headers.get("TypeSafe-Danger-Zone-Images")))
        if "assets" in body:
            raise JevError(400, "bad image")
        return {"answers": answers(), "usage": {"input_tokens": 10}}

    j = JevJudge(token="t", transport=transport)
    lab = j.label("1", "text", "photo", b"\xff\xd8\xff data")
    assert calls == [(True, "true"), (False, None)]
    assert not lab.image_used and j.input_tokens == 10


def test_classify_is_cached_and_records_failures():
    posts = pd.DataFrame(
        {"post_id": ["1", "2"], "text": ["a", "b"], "media_kind": [None, None],
         "media_urls": [[], []]}
    )  # fmt: skip

    class J:
        version = "v1"
        n = 0

        def label(self, post_id, text, media_kind, image):
            self.n += 1
            if post_id == "2":
                raise JevError(500, "boom")
            return PostLabels(post_id=post_id, label_version="v1", technical_rigor_score=3)

    j = J()
    first = run(posts, j, pd.DataFrame())
    assert first.set_index("post_id").loc["2", "error"].startswith("HTTP 500")
    run(posts, j, first)
    assert j.n == 3  # post 1 cached; only the failed post 2 retried


def test_kappa_and_agreement():
    assert cohen_kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0
    assert cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == pytest.approx(0.0)
    gold = pd.DataFrame(
        {"post_id": ["1", "2"], "hook_archetype": ["OTHER", "OTHER"], "visual_type": ["NONE"] * 2,
         "is_researcher_post": ["TRUE", "FALSE"], "technical_rigor_score": [3, 1]}
    )  # fmt: skip
    labels = pd.DataFrame(
        {"post_id": ["1", "2"], "hook_archetype": ["OTHER", "OTHER"], "visual_type": ["NONE"] * 2,
         "is_researcher_post": [True, True], "technical_rigor_score": [4, 4], "error": [None, None]}
    )  # fmt: skip
    r = agreement(gold, labels)
    assert r["researcher_accuracy"] == 0.5 and r["rigor_within_1"] == 0.5


def test_classify_treats_nan_media_kind_as_no_media():
    posts = pd.DataFrame(
        {"post_id": ["1"], "text": ["a"], "media_kind": [float("nan")], "media_urls": [[]]}
    )
    seen = []

    class J:
        version = "v1"

        def label(self, post_id, text, media_kind, image):
            seen.append(media_kind)
            return PostLabels(post_id=post_id, label_version="v1")

    run(posts, J(), pd.DataFrame())
    assert seen == [None]


def test_framing_questions_and_precedence():
    body = rubric.build_request("hello", "jev-latest")
    assert {f"framing_{f.value}" for f in rubric.FRAMING_QS} <= set(body["questions"])
    top = rubric.pick_framing({"CURIOSITY_GAP": 0.6, "OPEN_QUESTION": 0.9})[0]
    assert top is Framing.CURIOSITY_GAP
    assert rubric.pick_framing({"OPEN_QUESTION": 0.2, "DECLARATIVE_EMPIRICAL": 0.8})[0] is (
        Framing.DECLARATIVE_EMPIRICAL
    )
    assert rubric.pick_framing({"CURIOSITY_GAP": 0.1})[0] is Framing.DECLARATIVE_OTHER
    a = answers() | {"framing_OPEN_QUESTION": {"type": "noul", "noul": 0.8}}
    assert rubric.parse_answers("1", "v", a, None, False).framing is Framing.OPEN_QUESTION
    assert rubric.parse_answers("1", "v", answers(), None, False).framing is None  # v1 cache


def test_agreement_reports_framing_and_poster_role_when_present():
    gold = pd.DataFrame({"post_id": ["1", "2", "3"], "split": "pilot",
                         "is_researcher_post": ["yes", "no", "yes"],
                         "hook_archetype": ["OTHER"] * 3, "visual_type": ["NONE"] * 3,
                         "technical_rigor_score": [3, 2, 4],
                         "framing": ["OPEN_QUESTION", "DECLARATIVE_OTHER", "CURIOSITY_GAP"],
                         "poster_role": ["", "NON_RESEARCHER", ""]})  # fmt: skip
    model = gold.drop(columns=["split"]).assign(
        is_researcher_post=[True, False, True], error=None,
        framing=["OPEN_QUESTION", "DECLARATIVE_OTHER", "DECLARATIVE_OTHER"],
        poster_role=[None, "NON_RESEARCHER", None])  # fmt: skip
    r = agreement(gold, model)
    assert r["framing_n"] == 3 and r["poster_role_n"] == 1 and r["researcher_kappa"] == 1.0
    from src.enrichment.evaluate import report

    assert "## pilot" in report(gold, model)


def test_thread_cues_and_adapter_post_kind():
    from src.enrichment.rules import add_rule_features, thread_cues
    from src.ingestion.adapters import normalise_row

    assert thread_cues("1/6 Here is our new ablation study") == (True, 6)
    assert thread_cues("New ablation results (1/8)") == (True, 8)
    assert thread_cues("New results 🧵") == (True, 2)
    assert thread_cues("We cut memory by 1/2 the compute budget") == (False, 1)

    df = pd.DataFrame({
        "text": ["1/6 First post", "Plain post"],
        "media_count": [0, 0],
        "created_at": ["2026-10-01T00:00:00Z", "2026-10-02T00:00:00Z"],
        "post_kind": ["original", "original"],
    })
    out = add_rule_features(df)
    assert out["is_thread_opener"].tolist() == [True, False]
    assert out["thread_length"].tolist() == [6, 1]
    assert out["post_kind"].tolist() == ["thread_opener", "original"]

    norm = normalise_row({
        "id": "99", "userName": "u", "createdAt": "2026-10-01T00:00:00Z",
        "collected_at": "2026-10-10T00:00:00Z", "cohort": "ROSTER", "source": "apify",
        "followers": 500, "likes": 1, "replies": 0, "retweetCount": 0, "quoteCount": 0,
        "text": "A thread on tokenizers 🧵",
    })  # fmt: skip
    assert norm["post_kind"] == "thread_opener"


def test_classify_populates_poster_role_and_lazy_s2():
    from src.schema import PosterRole

    posts = pd.DataFrame({
        "post_id": ["1", "2", "3"],
        "author_handle": ["alice", "bob", "carol"],
        "author_name": ["Alice Smith", "Bob Jones", "Carol Plain"],
        "author_bio": ["PhD", "Builder", ""],
        "text": [
            "Check https://arxiv.org/abs/2608.00001",
            "Check https://arxiv.org/abs/2608.00001",
            "Just a normal post without paper",
        ],
        "paper_id": ["2608.00001", "2608.00001", None],
        "media_kind": [None, None, None],
        "media_urls": [[], [], []],
    })

    def fake_transport(body, _headers):
        if "paper_title" in body["state"]:
            return {"answers": {"own_work": {"noul": 0.1}, "bio": {"noul": 0.2}}, "usage": {}}
        return {"answers": answers(), "usage": {}}

    judge = JevJudge(token="t", transport=fake_transport)
    s2_calls = []
    out = run(
        posts,
        judge,
        pd.DataFrame(),
        paper_meta={"2608.00001": ("Title", "Alice Smith; Dan")},
        s2_lookup=lambda name: s2_calls.append(name) or 4,
    ).set_index("post_id")
    # Alice matched author list -> ORIGINAL without triggering S2;
    # Bob was NON -> S2 upgraded to CREDENTIALED; Carol had no paper
    assert out.loc["1", "poster_role"] == PosterRole.ORIGINAL_RESEARCHER
    assert out.loc["2", "poster_role"] == PosterRole.CREDENTIALED_RESEARCHER
    assert out.loc["2", "s2_papers"] == 4
    assert pd.isna(out.loc["3", "poster_role"])
    assert s2_calls == ["Bob Jones"]


def test_classify_concurrent_checkpoint_and_prob_serialisation(tmp_path):
    from src.enrichment.classify import _serialise_prob_cols

    posts = pd.DataFrame({
        "post_id": ["1", "2", "3"],
        "text": ["a", "b", "c"],
        "media_kind": [None, None, None],
        "media_urls": [[], [], []],
    })

    class J:
        version = "v2"

        def label(self, post_id, text, media_kind, image):
            return PostLabels(
                post_id=post_id, label_version="v2",
                archetype_probs={"OTHER": 0.9}, framing_probs={"OPEN_QUESTION": 0.1},
            )

    ckpt = tmp_path / "ckpt.parquet"
    out = _serialise_prob_cols(
        run(posts, J(), pd.DataFrame(), workers=2, checkpoint_path=ckpt, checkpoint_every=2)
    )
    assert ckpt.exists() and len(out) == 3
    assert all(isinstance(v, str) for v in out["archetype_probs"])
