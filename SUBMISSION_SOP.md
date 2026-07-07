# Competition Adapter SOP

This SOP applies only to `examples/competition_submission/`. The main open-source package is `gui_pilot/`.

## Fast Check

```bash
cd examples/competition_submission
zip -qr ../../submission_local.zip doc src
cd ../..
python3 tools/check_submission.py \
  --submission-dir examples/competition_submission \
  --zip submission_local.zip
```

This checks:

- competition tree contains exactly `doc/` and `src/`
- required files exist
- blocked cache/output artifacts are absent
- Python files compile
- common import modes work
- direct dependencies are declared
- zip size is under `20 MB`

## Dependency Check

```bash
python3 tools/check_submission.py \
  --submission-dir examples/competition_submission \
  --zip submission_local.zip \
  --check-pip-download \
  --pip-timeout 60
```

Use this only when network access to package indexes is available.

## Rule

The competition adapter is intentionally separate from `gui_pilot/`. For open-source development, change the package first; for competition compatibility, sync or vendor the required code into `examples/competition_submission/src/`.
