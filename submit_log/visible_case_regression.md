# Visible Case Regression Notes

Last updated: 2026-05-05

## Stable visible outcomes across strong versions

Observed from:

- `submit_log/v7c_log.md`
- `submit_log/v9_log.md`
- `submit_log/v10_log_1.md`
- `submit_log/v10_log_2.md`
- `submit_log/v11e_joint_log.md`
- `submit_log/v11e_vlmonly_log.md`
- `submit_log/v11_f_log.md`
- `submit_log/v11_g_log.md`

### Family A: LP review fill, then complete

Cases:

- `jingdong_lp_scene_1`
- `pinduoduo_sl_scene_2`

Shared invariant on good versions:

- Enter review flow
- Focus text area
- `TYPE` review text
- Immediately `COMPLETE`

Do not do:

- Do not hand post-`TYPE` control to broad VLM logic
- Do not auto-click generic bottom submit buttons after text input

### Family B: LP review fill, then one final click

Case:

- `douyin_lp_scene_0`

Shared invariant on better versions:

- Step 1: click lower-middle entry (`~[605,696]`)
- Step 2: click middle selector (`~[500,519]`)
- Step 3: click upper selector/rating-like target (`~[700,145]`)
- Step 4: click middle text area (`~[500,480]`)
- Step 5: `TYPE` review text
- Step 6: needs one more `CLICK`, not `COMPLETE`

Observed failure modes:

- `v7c`: fails too early at step 3
- `v9`/`v10`/`v11e`/`v11f`: reaches `TYPE`, then wrongly `COMPLETE`
- `v11g`: tries to click after `TYPE`, but click is unconstrained and wrong (`[95,970]`)

Safe design conclusion:

- This family should not use a broad "unknown app after TYPE => let VLM decide freely" rule.
- A narrow implicit-submit branch is acceptable only when the recent trajectory looks like:
  - upper selector/rating click
  - then middle text-box click
  - then `TYPE`

## Current safe guardrails

1. Keep `jingdong_lp_scene_1` and `pinduoduo_sl_scene_2` on hard regression watch:
   - `TYPE -> COMPLETE`
2. For hidden implicit-submit cases, never ask the VLM for a free-form action.
3. If an extra post-`TYPE` step is needed, restrict the model to coarse submit zones:
   - `TOP_RIGHT`
   - `BOTTOM_RIGHT`
   - `BOTTOM_CENTER`
   - `NONE`

## Why this matters

The strongest local and online baseline is not a heavier chain. It is:

- strong generic VLM fallback (`v9`-class)
- stable deterministic workflows for known one-key families
- very narrow post-`TYPE` repair for hidden review pages
