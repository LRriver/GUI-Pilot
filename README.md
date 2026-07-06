# GUI-Pilot

GUI-Pilot is a mobile GUI agent implementation for the Moonshot-style intelligent agent competition. The repository keeps the competition submission code, the official local runner scaffold, packaging checks, and a small set of regression notes from leaderboard iterations.

## Repository Layout

```text
.
├── submission/              # Final submission tree: doc/ and src/
├── code-for-student/        # Official scaffold and local test runner
├── tools/                   # Submission validation helpers
├── submit_log/              # Representative online logs and regression notes
├── submit_version/          # Local package manifest; zip artifacts are ignored
├── task.md                  # Competition task statement
└── SUBMISSION_SOP.md        # Pre-submit validation checklist
```

Large or private artifacts are intentionally not versioned:

- `.env`
- `code-for-student/test_data/`
- `code-for-student/output*/`
- `submit_version/*.zip`
- local IDE/agent settings

## Runtime

The competition submission targets Python 3.10.12. The current submission depends only on:

```text
openai
pillow
```

Local development in this workspace used the `moon_zx` conda environment.

## Configuration

Create a local `.env` from `.env.example` and fill in the VLM credentials:

```bash
cp .env.example .env
```

The default model constants used by the agent are:

```python
DEFAULT_API_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL_ID = "doubao-seed-1-6-vision-250815"
```

## Local Validation

Run the submission structure check:

```bash
conda activate moon_zx
cd submission
zip -qr ../submit_version/submission_local.zip doc src
cd ..
python tools/check_submission.py --submission-dir submission --zip submit_version/submission_local.zip
```

Run the official local runner when `code-for-student/test_data/` is available:

```bash
conda activate moon_zx
cd code-for-student
python test_runner.py --data_dir ./test_data/offline --output_dir ./output_local --no_debug_test
```

`output*` directories are generated artifacts and should not be committed.

## Packaging

The submitted archive must contain only:

```text
doc/
src/
```

Use `SUBMISSION_SOP.md` before every leaderboard submission. The repository keeps representative historical notes, but the current source of truth for code is `submission/src/agent.py`.
