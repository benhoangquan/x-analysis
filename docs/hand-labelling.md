# Hand-labelling guide

For Ben, labelling `data/gold/pilot_sheet.csv` now and `data/gold/label_sheet.csv` (the 200-post set) later. The authoritative definitions are in AGENTS.md §3 and `notes/30_concepts/`; this page is the form spec.

## How to label

1. Open the post from `url` when `media_kind` is set or the text is cut off. Judge what a reader on X sees: text, image, video, link card.
2. Fill every label column. Leave `poster_role` empty when `paper_link` is empty.
3. Label without looking up Jev's labels. The sheet hides them on purpose.
4. Write a `note` whenever you choose `OTHER` or `OTHER_IMAGE`: a few words on what the post is (for example "paper announcement", "job ad", "conference photo"). The enum revision in milestone 3 is built from these notes. Add a note on any other post you found hard.
5. Save the filled file as `data/gold/pilot_labels.csv` (pilot) or `data/gold/hand_labels.csv` (200-post set).

## Columns

**`is_researcher_post`**: `yes` or `no`. Is the post written for people who read or write ML research papers (faculty, PhD students, research scientists and engineers, practitioners sharing training or fine-tuning detail)? Product posts aimed at them count, Tiptree's included. Posts for app developers, AI-tool shoppers, investors or the general public do not. Judge the intended reader only, not how rigorous the post is.

**`hook_archetype`**: one value. When two fit, take the one higher in this list.

| Value | The post… |
|---|---|
| `VISUAL_MAP` | shows a map or graph of a research area or paper cluster |
| `PRODUCT_DEMO` | shows a tool doing a tedious researcher task |
| `TECHNICAL_BREAKDOWN` | dissects a paper's figure, an ablation or an architecture |
| `LITERATURE_SYNTHESIS` | connects 3 or more papers to show a gap |
| `CONTESTED_CLAIM` | challenges a prevailing view or points to an empirical contradiction |
| `HOT_TAKE_CULTURE` | gives an opinion on peer review, GPU access or lab life |
| `OTHER` | none of the above (write a `note`) |

**`visual_type`**: `NONE` (text only, link card counts as none), `LACUNA_MAP` (map or network of papers or topics), `PAPER_FIGURE` (table, loss curve, architecture diagram from a paper), `CODE_TERMINAL` (code or command line), `VIDEO_DEMO` (screen recording or UI walkthrough), `OTHER_IMAGE` (anything else; write a `note`).

**`technical_rigor_score`**: 1 to 5.

| Score | Anchor |
|---|---|
| 1 | Introductory or promotional: general claims, no technical specifics |
| 2 | Informal technical remark: names a method or model, no numbers or evidence |
| 3 | Specific claim: cites a paper, a result or a number without saying how it was measured |
| 4 | Detailed empirical discussion: compares methods or settings with measurements, baselines or ablations |
| 5 | Formal or benchmark-level: formal maths, a named benchmark or venue result, concrete hyperparameters |

**`framing`**: one value. When two fit, take the one higher in this list.

| Value | The post… |
|---|---|
| `CURIOSITY_GAP` | withholds the payoff so you click or expand ("Do you know why…", "Here's why…") |
| `OPEN_QUESTION` | asks an open technical question and leaves it unanswered |
| `DECLARATIVE_EMPIRICAL` | states a specific empirical result: a number, a comparison, a benchmark score |
| `DECLARATIVE_OTHER` | any other statement: announcement, summary, opinion |

A rhetorical question the post answers itself is not `OPEN_QUESTION`.

**`poster_role`**: only when `paper_link` is set. One value, highest first.

| Value | The poster… |
|---|---|
| `ORIGINAL_RESEARCHER` | is an author of the linked paper, or the official account of the authors' lab |
| `CREDENTIALED_RESEARCHER` | is not an author but has field credentials: at least 3 ML papers, or a stated research position |
| `NON_RESEARCHER` | is neither |

Check the arXiv author list from `paper_link`, and the poster's bio or Google Scholar when unsure.

## Admission review

`data/gold/admission_review.csv` holds 75 roster candidates, shuffled: Jev admitted some and rejected others, and the sheet does not say which. For each, open `profile` if the bio and posts are not enough, then fill:

- **`ben_admit`**: `yes` if the account mostly writes for people who read or write ML research papers (the same reader test as `is_researcher_post`, applied to the account), otherwise `no`. Organisations count as `no` unless you think labs belong in the roster; say so in the note.
- **`ben_note`**: a few words on any `no`, and on any case you found hard.

Save it as `data/gold/admission_review_done.csv`. Takes about 30 minutes.

## Pilot

The pilot is 40 v0 posts (10 per follower tier, at most 2 per author, 7 with a paper link), drawn from authors likely to join the roster. It tests the guide and the columns before the 200-post set. Whether pilot labels count toward that set is decided in the pre-run review.
