# Visible Case Regression Notes

Last updated: 2026-05-05

## Stable visible outcomes across strong versions

Observed from:

- `submit_log/v7c_log.md`
- `submit_log/v9_log.md`
- `submit_log/v9_2_log.md`
- `submit_log/v10_log_1.md`
- `submit_log/v10_log_2.md`
- `submit_log/v11e_joint_log.md`
- `submit_log/v11e_vlmonly_log.md`
- `submit_log/v11_f_log.md`
- `submit_log/v11_g_log.md`
- `submit_log/v12a_log.md`

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
- `v12a`: reaches `TYPE`, then still returns local zero-token `COMPLETE`; the implicit-submit guard did not trigger online.

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
4. Online runner history may be thinner than local runner history. For trajectory-based guards, combine `history_actions` with this agent's own compact `_history`.

## Broader Case-Family Backlog

These families are visible from online logs and local datasets, but are not all fully covered by the current regression table yet.

### Video search / playback / comment

Examples:

- `step_aiqiyi_onekey_0011`
- local `step_bilibili_onekey_0008`
- local `step_tengxunshipin_onekey_0005`
- local `step_mangguo_onekey_0008`
- local `step_ximalaya_onekey_0001`

Current status:

- Local workflows are stable.
- Online visible logs show `step_aiqiyi_onekey_0011` uses zero-token workflow steps and reaches at least the comment-send path.
- Need keep these workflows isolated from generic VLM fallback changes.

### Map / taxi / route

Examples:

- local `step_baidumap_onekey_0008`
- local `step_baidumap_onekey_0010`

Current status:

- Local workflows are stable.
- Generic fallback needs strict origin/destination distinction when workflows do not match.

### Food ordering / purchase

Examples:

- local `step_meituan_onekey_0001`
- online e-commerce LP/SL review scenes

Current status:

- Local food ordering is workflow-driven and should not be affected by review-postsubmit guards.
- E-commerce review scenes must preserve `TYPE -> COMPLETE`.

### Flight / travel form

Examples:

- local `step_quonekey_0030`

Current status:

- Local workflow is stable.
- Future hidden cases likely need form-state tracking: origin, destination, date, sorting/price visibility.

## Immediate improvement candidates

1. Fix `douyin_lp_scene_0` with a narrow post-`TYPE` implicit-submit path that can still trigger when online `history_actions` only exposes the last action.
2. Do not reintroduce candidate/critic chains until a small A/B shows a family-level gain; broad heavy chains previously degraded online scores.
3. For each new online log, add one row to this file before changing prompts or workflows.

## Why this matters

The strongest local and online baseline is not a heavier chain. It is:

- strong generic VLM fallback (`v9`-class)
- stable deterministic workflows for known one-key families
- very narrow post-`TYPE` repair for hidden review pages
