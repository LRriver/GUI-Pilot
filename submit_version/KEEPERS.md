# Local Submission Package Notes

Zip packages are intentionally ignored by Git to keep this repository small and source-focused. Locally, the minimal retained package set after cleanup was:

| Package | Known online score | Reason |
| --- | ---: | --- |
| `submission_v7c.zip` | 58.62 | Best v7-family package; useful as alternate high-score behavior reference. |
| `submission_v9.zip` | 58.62 | Best v9-family package; main historical best baseline. |
| `submission_v12b.zip` | not submitted yet | Current latest candidate package. |

Removed:

- Older low-score packages and archived redundant versions.
- Heavy multi-sample critic packages.
- Reference projects under `refer_pro/`.
- Original attachment zip `1776137151181_bf4cdr2t_6915.zip`.

Local test output retained:

- None. Generated `output*` directories were removed to keep the workspace small; rerun tests when fresh artifacts are needed.

Original/local test data retained:

- `code-for-student/test_data`

When cloning from GitHub, regenerate package zips from `submission/` with `tools/check_submission.py`.
