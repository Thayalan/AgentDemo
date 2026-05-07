<img width="1920" height="5149" alt="screencapture-localhost-8501-2026-05-07-10_30_29" src="https://github.com/user-attachments/assets/88f80841-6cae-4108-8c28-61843cf53cd3" />

# CI/CD Log Analyzer

This project reads sample CI/CD log files from the `logs/` folder and generates concise triage reports in Markdown format under the `output/` folder.

## Overview

- `main.py` analyzes CI/CD logs and writes structured reports in `output/`.
- `streamlit_app.py` provides a web UI for uploading log files and viewing triage summaries interactively.
- Supported upload formats in the Streamlit app: `.log`, `.txt`, `.pdf`, `.docx`.

## Requirements

Install the required Python packages before running the app:

```bash
pip install streamlit python-docx pypdf
```

## CLI Usage

1. Place `.log` files into the `logs/` folder.
2. Run:

```bash
python main.py
```

3. Open the generated Markdown files in `output/`.
   - Each log file produces its own report such as `ci_cd_triage_report_build_application.md`, `ci_cd_triage_report_deploy_release.md`, or `ci_cd_triage_report_test_suite.md`.

## Streamlit Web UI

Run the interactive analyzer:

```bash
streamlit run streamlit_app.py
```

Upload a supported log file and review:

- file preview
- detected error entries
- inferred failed stage
- most common root cause
- detailed error summary
- suggested fixes
- confidence scores

## Sample log file set

This repository includes the following sample log categories:

- `logs/sample_build.log` — build and compilation failures
- `logs/sample_deploy.log` — deployment and Kubernetes issues
- `logs/sample_test.log` — test failures, runtime errors, and missing dependencies

## Report structure

Each generated report includes:

- title
- summary paragraph
- failed stage
- error type
- line number
- error snippet
- root cause
- suggested fixes
- confidence
