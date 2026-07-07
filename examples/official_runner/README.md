# Official Runner Scaffold

This directory preserves the original local-runner scaffold used by the source competition. It is kept as a reference adapter, not as the primary GUI-Pilot API.

It has a separate dependency set:

```bash
cd examples/official_runner
pip install -r requirements.txt
```

The original runner expects local `test_data/`, which is intentionally ignored by Git because it is large and not required by the open-source package.

For normal GUI-Pilot usage, import the package from the repository root instead:

```python
from gui_pilot import GuiPilotAgent
```
