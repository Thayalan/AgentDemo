from pathlib import Path
import re
import datetime

LOG_DIR = Path("logs")
OUTPUT_DIR = Path("output")

ERROR_PATTERNS = [
    re.compile(r"(?P<file>[^\s:]+\.cs)\((?P<line>\d+),(?P<col>\d+)\): error (?P<code>CS\d+): (?P<message>.+)", re.IGNORECASE),
    re.compile(r"(?P<file>[^\s:]+\.py):(?P<line>\d+): (?P<error>.+)", re.IGNORECASE),
    re.compile(r"error:\s*(?P<message>.+)", re.IGNORECASE),
    re.compile(r"failed to (?P<message>.+)", re.IGNORECASE),
    re.compile(r"AssertionError:\s*(?P<message>.+)", re.IGNORECASE),
]

STAGE_PATTERNS = [
    re.compile(r"Step[:\s]+(?P<stage>.+)", re.IGNORECASE),
    re.compile(r"Stage[:\s]+(?P<stage>.+)", re.IGNORECASE),
    re.compile(r"Job [:\s]+(?P<stage>.+)", re.IGNORECASE),
    re.compile(r"##\[error\]Agent\.Provisioning.*", re.IGNORECASE),
]

SUGGESTION_MAP = {
    "syntax error": "Check the source file at the indicated line for missing punctuation, braces, or malformed code.",
    "null reference": "Verify the variable is initialized before use and add null checks where appropriate.",
    "404": "Confirm the requested resource exists and verify the endpoint URL or deployment configuration.",
    "500": "Inspect the server or application logs around the failing request to identify the failing component.",
    "failed to build": "Validate dependencies, update package references, and rerun the build in a clean workspace.",
    "assertionerror": "Review the failed assertion and adjust the expected value or the test conditions.",
    "type or namespace name": "Add the required namespace import or package reference for the missing type, then rebuild.",
    "does not exist in the current context": "Confirm the symbol is declared in the current scope and spelled correctly, or initialize it before use.",
    "unable to recognize": "Verify manifest syntax, API version, and resource kind before reapplying the Kubernetes manifest.",
}

CONFIDENCE_BASE = {
    "high": 0.8,
    "medium": 0.6,
    "low": 0.4,
}


def load_log_files(directory: Path):
    return sorted(directory.glob("*.log"))


def report_filename_for_stage(stage: str):
    key = re.sub(r"[^a-z0-9]+", "_", stage.lower()).strip("_")
    if not key:
        key = "unknown"
    return OUTPUT_DIR / f"ci_cd_triage_report_{key}.md"


def detect_stage(lines):
    for line in lines:
        for pattern in STAGE_PATTERNS:
            match = pattern.search(line)
            if match:
                stage = match.groupdict().get("stage") or match.groupdict().get("step")
                if stage:
                    return stage.strip()
    return "Unknown"


def parse_errors(lines):
    errors = []
    for index, line in enumerate(lines, start=1):
        for pattern in ERROR_PATTERNS:
            match = pattern.search(line)
            if match:
                data = match.groupdict()
                message = data.get("message") or data.get("error") or line.strip()
                errors.append({
                    "error_type": data.get("code") or data.get("error") or message.strip(),
                    "line_number": data.get("line") or str(index),
                    "error_snippet": line.strip(),
                    "raw_message": message.strip(),
                })
                break
    return errors


def infer_root_cause(error_text: str):
    text = error_text.lower()
    if "expected" in text and "got" in text:
        return "Test assertion mismatch or unexpected response payload."
    if "missing" in text or "expected" in text or "syntax" in text:
        return "Code syntax or formatting issue in the failing source path."
    if "null reference" in text or "none" in text:
        return "Null or undefined value accessed during execution."
    if "failed to build" in text or "error cs" in text:
        return "Build configuration or source compilation failure."
    if "timeout" in text:
        return "Long-running step exceeded its allowed execution time."
    return "The failure originates from the reported error message or the failing command."


def suggest_fix(error_text: str, error_code: str = ""):
    text = error_text.lower()
    code = error_code.lower()
    if "cs1002" in code or "; expected" in text:
        return (
            "Add the missing semicolon or complete the statement at the reported source line. "
            "Then rebuild the project and verify the surrounding code block is syntactically correct."
        )
    if "cs0103" in code or "does not exist in the current context" in text:
        return (
            "Confirm the referenced symbol is declared in the active scope and spelled correctly. "
            "Initialize or import the symbol before use, then retry the build."
        )
    if "cs0246" in code or "type or namespace name" in text:
        return (
            "Add the missing namespace import or assembly/package reference for the type, "
            "restore dependencies, and rebuild the solution."
        )
    if "cs1061" in code or "does not contain a definition for" in text:
        return (
            "Use a member that actually exists on the object type or change the object to the correct type. "
            "Check for missing extension methods, imports, or incorrect API usage."
        )
    if "apps/v2" in text:
        return (
            "Update the Kubernetes manifest to a supported API version such as apps/v1. "
            "Validate the resource kind against cluster-supported API resources and reapply the manifest."
        )
    if "unable to recognize" in text and "kind" in text:
        return (
            "Confirm the manifest kind and API version are valid for the cluster. "
            "Fix the YAML, then rerun kubectl apply."
        )
    if "assertionerror" in text or "assertion error" in text:
        return (
            "Review the expected value versus the actual result and fix the test or application output. "
            "Adjust the assertion or the data setup so the observed behavior matches the expected behavior."
        )
    if "timeout" in text:
        return (
            "Increase the step timeout if this operation is expected to take longer, or optimize the task so it completes within the CI window."
        )
    for key, suggestion in SUGGESTION_MAP.items():
        if key in text:
            return suggestion
    if "build" in text:
        return SUGGESTION_MAP["failed to build"]
    return (
        "Analyze the failing log lines, resolve the reported error in the source or manifest, "
        "and rerun the CI job once the underlying issue is fixed."
    )


def confidence_score(error_text: str):
    text = error_text.lower()
    if any(key in text for key in ["failed to build", "cs", "syntax", "assertionerror", "null reference"]):
        return CONFIDENCE_BASE["high"]
    if any(key in text for key in ["error:", "failed", "timeout"]):
        return CONFIDENCE_BASE["medium"]
    return CONFIDENCE_BASE["low"]


def build_report(entries, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    title = "CI/CD Error Triage Report"
    summary = (
        "This report summarizes the primary CI/CD failures detected in sample logs, "
        "including the failed stage, error details, root cause, and recommended fixes."
    )
    ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30), name="IST")
    lines = [
        f"# {title}",
        "",
        summary,
        "",
        f"Generated: {datetime.datetime.now(ist):%Y-%m-%d %H:%M IST}",
        ""
    ]

    if not entries:
        lines.extend(["## Summary", "", "No failures were detected in the input log files."])
    else:
        for entry in entries:
            lines.extend([
                f"## {entry['title']}",
                "",
                f"**Summary:** {entry['summary']}",
                "",
                f"- **Failed stage:** {entry['failed_stage']}",
                f"- **Error type:** {entry['error_type']}",
                f"- **Line number:** {entry['line_number']}",
                f"- **Error snippet:** `{entry['error_snippet']}`",
                f"- **Root cause:** {entry['root_cause']}",
                f"- **Suggested fixes:** {entry['suggested_fixes']}",
                f"- **Confidence:** {entry['confidence']:.0%}",
                ""
            ])

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote triage report to {output_path}")


def analyze_log_file(path: Path):
    raw_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if not raw_lines:
        return []

    stage = detect_stage(raw_lines)
    error_entries = parse_errors(raw_lines)
    if not error_entries:
        return []

    results = []
    for index, error_data in enumerate(error_entries, start=1):
        raw_message = error_data["raw_message"]
        root_cause = infer_root_cause(raw_message)
        suggestion = suggest_fix(raw_message, error_data["error_type"])
        confidence = confidence_score(raw_message)
        title = path.stem.replace("_", " ").title()
        if len(error_entries) > 1:
            title = f"{title} - Error {index}"

        results.append({
            "title": title,
            "summary": f"Detected a failure in the {stage} stage with an error message from the log.",
            "failed_stage": stage,
            "error_type": error_data["error_type"],
            "line_number": error_data["line_number"],
            "error_snippet": error_data["error_snippet"],
            "root_cause": root_cause,
            "suggested_fixes": suggestion,
            "confidence": confidence,
        })

    return results


def main():
    log_files = load_log_files(LOG_DIR)

    if not log_files:
        print(f"No log files found in {LOG_DIR.resolve()}. Place sample .log files in that folder.")
        return

    for log_path in log_files:
        results = analyze_log_file(log_path)
        if not results:
            print(f"No actionable error found in {log_path.name}")
            continue

        report_path = report_filename_for_stage(results[0]["failed_stage"])
        build_report(results, report_path)


if __name__ == "__main__":
    main()
