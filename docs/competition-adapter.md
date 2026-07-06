# Competition Adapter

The original competition expected a zip with exactly:

```text
doc/
src/
```

This repository keeps that format as an example under:

```text
examples/competition_submission/
```

Build and validate:

```bash
cd examples/competition_submission
zip -qr ../../submission_local.zip doc src
cd ../..
python tools/check_submission.py \
  --submission-dir examples/competition_submission \
  --zip submission_local.zip
```

The adapter is not the main open-source API. The main API is:

```python
from gui_pilot import GuiPilotAgent
```

When preparing a real competition submission, make sure the adapter is self-contained according to the competition rules.
