# Submission SOP

Use this SOP before every leaderboard submission.

## Fast check

Run this after any code change:

```bash
source /root/anaconda3/etc/profile.d/conda.sh
conda activate zh_moon
python tools/check_submission.py --submission-dir submission --zip submission.zip
```

This checks:

- submission structure is exactly `doc/` and `src/`
- required files exist
- blocked artifacts such as `__pycache__` and `output/` are absent
- all Python files compile
- both common import modes work
- `requirements.txt` covers imported third-party packages
- direct dependencies stay small and match current imports
- the zip is under `20 MB`

## Final strict check

Run this right before packaging or submitting:

```bash
source /root/anaconda3/etc/profile.d/conda.sh
conda activate zh_moon
python tools/check_submission.py \
  --submission-dir submission \
  --zip submit_version/YOUR_SUBMISSION.zip \
  --check-pip-download \
  --pip-timeout 60
```

This adds a network-sensitive dependency check by running `pip download -r submission/src/requirements.txt`.

If this step fails, do not submit yet.

## Packaging rule

Before zipping, make sure the latest main logic has been synced into `submission/src/agent.py`.

After zipping, run:

```bash
source /root/anaconda3/etc/profile.d/conda.sh
conda activate zh_moon
python tools/check_submission.py \
  --submission-dir submission \
  --zip submit_version/YOUR_SUBMISSION.zip \
  --check-pip-download \
  --pip-timeout 60
```

Only submit the zip that passed this exact check.

## Decision rule

- `PASS` with no errors: safe to submit
- `FAIL`: do not submit
- warnings only: submit only after reading the warning list

## Why this exists

This script is meant to catch the common failure classes that waste leaderboard attempts:

- wrong zip structure
- extra cache or log files in the package
- missing or mismatched dependency declarations
- import path issues between local and remote startup modes
- stale vendored fallback code that is no longer used by the main agent
- dependency install risk on the remote mirror
