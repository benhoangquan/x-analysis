import pandas as pd

from src.enrichment.label_sheet import LABEL_FIELDS, make_sheet
from src.ingestion.panel import arxiv_ids


def test_arxiv_ids_need_arxiv_context():
    item = {
        "text": "Released in 2025.1234 builds. See arXiv:2510.01234",
        "entities": {"urls": [{"expanded_url": "https://huggingface.co/papers/2509.99999"}]},
    }
    assert arxiv_ids(item) == ["2509.99999", "2510.01234"]


def test_arxiv_ids_from_modelscope_paper_page():
    item = {"entities": {"urls": [{"expanded_url": "https://modelscope.ai/papers/2606.07229"}]}}
    assert arxiv_ids(item) == ["2606.07229"]


def test_arxiv_ids_from_pdf_link_with_version():
    assert arxiv_ids({"text": "https://arxiv.org/pdf/2511.00001v2"}) == ["2511.00001"]


def _posts() -> pd.DataFrame:
    rows = []
    for t in ["<2k", "2k-20k", "20k-200k", ">200k"]:
        for a in range(4):
            for k in range(3):
                rows.append(dict(post_id=f"{t}{a}{k}", author_handle=f"{t}a{a}", follower_tier=t,
                                 url="u", media_kind=None, text="x", eligible=True))
    return pd.DataFrame(rows)


def test_sheet_is_stratified_capped_and_blind():
    s = make_sheet(_posts(), per_tier=5, paper_links={"<2k00": ["2510.00001"]}, max_per_author=2)
    assert s.groupby("tier").size().eq(5).all()
    assert s.groupby("author_handle").size().max() <= 2
    assert all((s[c] == "").all() for c in LABEL_FIELDS)
    assert not {"hook_archetype_prob", "is_researcher_prob"} & set(s.columns)
