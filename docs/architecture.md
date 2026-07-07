# Architecture

GUI-Pilot separates stable mobile GUI execution from high-budget research exploration.

## Public Facade

`GuiPilotAgent` is the public entrypoint:

```python
from gui_pilot import GuiPilotAgent

agent = GuiPilotAgent(profile="lite")
```

The facade delegates to a profile implementation:

- `LiteAgent` for the default stable pipeline.
- `DeepAgent` for the high-budget planning/review pipeline.

## Lite Pipeline

```text
Instruction
-> app extraction
-> text-entry guards
-> workflow priors
-> VLM fallback
-> parser and validator
```

`lite` is optimized for stable end-to-end task completion. It avoids broad post-hoc rewrites and only applies high-confidence guards.

## Deep Pipeline

```text
Instruction + screenshot
-> TaskPlanner
-> VisualCropper
-> CandidateSampler
-> CandidateCritic
-> ActionArbiter
-> ReflectionMemory
```

`deep` is a research profile. In the current implementation, planning, crop proposals, and reflection memory are diagnostic trace layers around the reliable `lite` action generator; arbitration can choose among generated candidates, but crop-conditioned VLM calls and memory-fed reflection are intentionally left as extension points.

## Action Schema

All profiles return the same `AgentOutput` schema:

- `CLICK`: `{"point": [x, y]}`
- `TYPE`: `{"text": "..."}`
- `SCROLL`: `{"start_point": [x1, y1], "end_point": [x2, y2]}`
- `OPEN`: `{"app_name": "..."}`
- `COMPLETE`: `{}`

Coordinates are normalized to `[0, 1000]`.
