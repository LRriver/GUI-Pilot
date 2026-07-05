# Representative Submission Versions

This folder keeps representative packages by strategy family. Lower-scoring or superseded packages are moved to `archive_redundant/`.

## Kept Packages

| Package | Known online score | Strategy family | Keep reason |
| --- | ---: | --- | --- |
| `submission_v1.zip` | 37.93 in `submit_log/v1._log.md` | early baseline | Early reference baseline. User previously noted it was one of the better early submissions. |
| `submission_v5b.zip` | 34.48 in `submit_log/v5b_log.md` | early workflow/VLM hybrid | Representative of the early workflow route before v7. |
| `submission_v7c.zip` | 58.62 in `submit_log/v7c_log.md` | conservative high-score workflow/VLM hybrid | Best scored v7-family package. Different failure shape from v9 on `douyin_lp_scene_0`. |
| `submission_v9.zip` | 58.62 in `submit_log/v9_log.md`; 51.72 rerun in `submit_log/v9_2_log.md` | v9 generic fallback + workflow guard | Best scored v9-family package and important variance reference. |
| `submission_v11e_vlmonly.zip` | 48.28 in `submit_log/v11e_vlmonly_log.md` | VLM-only / workflow-disabled route | Best logged VLM-only submitted package. |
| `submission_v12a.zip` | 55.17 in `submit_log/v12a_log.md` | v9-rebased implicit-submit attempt | Scored package for v12 route; useful because it showed the trigger gap. |
| `submission_v12b.zip` | not submitted / no online score yet | current candidate | Latest package after self-history implicit-submit trigger fix. |
| `submission_20260410_multisamplecritic_cap2_parallel_v1.zip` | 17.24 in `submit_log/submission_20260410_multisamplecritic_cap2_parallel_v1_log.md` | heavy multi-sample critic | Representative submitted heavy-chain attempt. |
| `submission_20260410_multisamplecritic_map23_v1.zip` | no online log found | heavy map/candidate route | Kept as a distinct historical heavy-chain reference. |

## Archived Packages

`archive_redundant/` contains lower-scoring or superseded packages from the same broad routes, such as v2, v6, v7, v7b, v8, v10, v11 joint/f/g variants.

## Test Output Retention

Only one local test output is kept:

- `code-for-student/output_v12b_full`

All other `code-for-student/output*` directories were removed because their `visualization/*/summary.png` files accounted for most disk usage.
