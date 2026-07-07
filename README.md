# GUI-Pilot

GUI-Pilot is an open-source mobile GUI Agent framework built around two practical execution profiles:

- **`lite`**: a fast, stable profile based on workflow priors, a single VLM fallback, and narrow post-action guards.
- **`deep`**: a high-budget research profile with planning, crop proposals, candidate sampling, review, arbitration, and reflection memory.

The project is designed for tasks where an agent receives a natural-language instruction plus a mobile screenshot and returns the next GUI action:

```text
OPEN(app_name)
CLICK(point=[x, y])
TYPE(text)
SCROLL(start_point=[x1, y1], end_point=[x2, y2])
COMPLETE()
```

Coordinates use normalized `[0, 1000]` screen coordinates.

## Why GUI-Pilot Exists

Mobile GUI automation fails in small ways: one wrong tap, one premature `TYPE`, one extra click after text entry, or one early `COMPLETE` breaks the whole task. GUI-Pilot therefore combines deterministic structure with VLM perception:

```text
Instruction + screenshot + action history
        │
        ▼
Task parsing and context summarization
        │
        ▼
Workflow priors for high-confidence task families
        │
        ▼
VLM fallback for unknown screens
        │
        ▼
Postprocess guards and action validation
        │
        ▼
Next GUI action
```

The default profile does not try to be an unconstrained ReAct loop. It uses VLMs where visual judgment is needed and keeps known high-risk states guarded by deterministic logic.

## Install

```bash
git clone git@github.com:LRriver/GUI-Pilot.git
cd GUI-Pilot
pip install -e .
```

Create local credentials:

```bash
cp .env.example .env
# GUI-Pilot does not auto-load .env. Export variables in your shell:
set -a; source .env; set +a
```

The bundled `BaseAgent` uses an OpenAI-compatible vision model API. The default constants are:

```python
DEFAULT_API_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL_ID = "doubao-seed-1-6-vision-250815"
```

## Quick Start

```python
from gui_pilot import GuiPilotAgent

agent = GuiPilotAgent(profile="lite")
```

For a high-budget pipeline:

```python
from gui_pilot import GuiPilotAgent, GuiPilotConfig

agent = GuiPilotAgent(
    config=GuiPilotConfig(
        profile="deep",
        candidate_count=3,
        enable_cropping=True,
        enable_reflection=True,
    )
)
```

Runnable examples:

```bash
python3 examples/quickstart_lite.py
python3 examples/quickstart_deep.py
```

The examples use synthetic screenshots for import and API-shape smoke tests. Real GUI execution requires a runner that supplies `AgentInput` screenshots and applies returned actions.

## Profiles

### `lite`: stable execution profile

`lite` is the default. It is intentionally simple and close to the strongest stable competition-era design.

Pipeline:

```text
TaskParser
-> WorkflowPrior
-> Single VLM Fallback
-> Text/Submit Guards
-> Output Parser
-> Action Validator
```

What it does well:

- Opens the target app directly when the instruction names one.
- Uses narrow workflow priors for common mobile task families: search, video playback, comments, food ordering, map/travel forms, and reviews.
- Falls back to VLM observation when no high-confidence workflow matches.
- Protects text-entry states, especially whether to `COMPLETE` after typing or click a send/submit button.
- Keeps dependencies small: `openai` and `pillow`.

This is the recommended production-style profile.

### `deep`: high-budget research profile

`deep` is the experimental profile for cases where inference cost is less important than robustness and observability.

Pipeline:

```text
TaskPlanner
-> VisualCropper
-> CandidateSampler
-> CandidateCritic
-> ActionArbiter
-> ReflectionMemory
```

The current implementation reuses `lite` as the reliable action generator, then layers high-budget diagnostics and arbitration around it:

- `planner.py`: produces coarse subgoals for traceability.
- `cropper.py`: proposes stable UI regions such as top bar, content, bottom bar, and right-side action zones for diagnostics.
- `sampler.py`: generates and de-duplicates action candidates.
- `critic.py`: scores candidates with task-stage and action-risk heuristics.
- `arbiter.py`: chooses the best candidate deterministically.
- `memory.py`: keeps bounded trace memory for debugging and future reflection; it is not yet fed back into action decisions.

`deep` is intended as a research surface for adding stronger crop-conditioned VLM calls, richer review prompts, and ReAct/plan-execute loops without making the default agent fragile.

## Repository Layout

```text
.
├── gui_pilot/
│   ├── agent.py                  # GuiPilotAgent(profile=...)
│   ├── schema.py                 # BaseAgent, AgentInput, AgentOutput, actions
│   ├── config.py                 # profile and deep-pipeline configuration
│   ├── profiles/
│   │   ├── lite.py               # stable lightweight profile
│   │   └── deep.py               # high-budget profile
│   └── deep/                     # planner/cropper/sampler/critic/arbiter/memory
├── examples/
│   ├── quickstart_lite.py
│   ├── quickstart_deep.py
│   ├── competition_submission/   # adapter for the original competition format
│   └── official_runner/          # original local runner scaffold
├── docs/
│   ├── architecture.md
│   ├── strategy-profiles.md
│   ├── competition-adapter.md
│   └── regression-notes.md
├── tests/
└── tools/
```

## Competition Adapter

The original competition required a zip containing only:

```text
doc/
src/
```

That compatibility tree now lives under [`examples/competition_submission/`](examples/competition_submission/). It is an adapter/example, not the main project entrypoint.

See [`docs/competition-adapter.md`](docs/competition-adapter.md) for packaging commands.

## Regression Notes

The old leaderboard logs are not part of the runtime. Their useful content has been summarized in [`docs/regression-notes.md`](docs/regression-notes.md): stable task families, known failure modes, and guardrails that motivated the current design.

## Development Checks

Run unit/import tests:

```bash
python3 -m unittest discover -s tests -v
```

Check the competition adapter:

```bash
cd examples/competition_submission
zip -qr ../../submission_local.zip doc src
cd ../..
python3 tools/check_submission.py \
  --submission-dir examples/competition_submission \
  --zip submission_local.zip
```

The `examples/official_runner/` tree is an archival scaffold for the original local runner. It has its own `requirements.txt`, and its test data is intentionally not tracked in this repository.

Generated zips, local datasets, screenshots, outputs, and `.env` are ignored by Git.
