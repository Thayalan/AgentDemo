# CI/CD Log Analyzer

This project reads sample CI/CD log files from the `logs/` folder and generates a concise triage report in Markdown format under the `output/` folder.

## Usage

1. Place `.log` files into the `logs/` folder.
2. Run:

```bash
python main.py
```

3. Open the generated Markdown files in `output/`.
   - Each log file produces its own report like `ci_cd_triage_report_build_application.md`, `ci_cd_triage_report_deploy_release.md`, or `ci_cd_triage_report_test_suite.md`.

## Sample log file set

This repository keeps exactly three sample log categories:

- `logs/sample_build.log` — build and compilation failures
- `logs/sample_deploy.log` — deployment and Kubernetes issues
- `logs/sample_test.log` — test failures, runtime errors, and missing dependencies

## Report structure

- title
- summary paragraph
- failed stage
- error type
- line number
- error snippet
- root cause
- suggested fixes
- confidence
