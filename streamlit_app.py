import streamlit as st
import re
from pathlib import Path
from collections import Counter
from pypdf import PdfReader
from docx import Document

from main import analyze_log_text

# Function to read file content based on type
def read_file_content(uploaded_file):
    file_extension = Path(uploaded_file.name).suffix.lower()
    if file_extension in ['.txt', '.log']:
        return uploaded_file.read().decode('utf-8')
    elif file_extension == '.pdf':
        pdf_reader = PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    elif file_extension == '.docx':
        doc = Document(uploaded_file)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    else:
        return None

# Function to extract error lines
def extract_errors(text):
    error_patterns = [
        re.compile(r'.*ERROR.*', re.IGNORECASE),
        re.compile(r'.*Exception.*', re.IGNORECASE),
        re.compile(r'.*failed.*', re.IGNORECASE),
        re.compile(r'.*failure.*', re.IGNORECASE),
        re.compile(r'.*traceback.*', re.IGNORECASE),
    ]
    lines = text.split('\n')
    error_lines = []
    for line in lines:
        for pattern in error_patterns:
            if pattern.match(line.strip()):
                error_lines.append(line.strip())
                break
    return error_lines[:10]  # Top 10 error lines

# Function to infer likely failure reason
def infer_failure_reason(error_lines):
    if not error_lines:
        return "No clear error details detected."
    # Simple heuristic: look for common keywords
    reasons = []
    for line in error_lines:
        if 'timeout' in line.lower():
            reasons.append("Timeout issue")
        elif 'permission' in line.lower() or 'forbidden' in line.lower():
            reasons.append("Permission or access issue")
        elif 'connection' in line.lower():
            reasons.append("Connection or network issue")
        elif 'syntax' in line.lower():
            reasons.append("Syntax error")
        elif 'build' in line.lower():
            reasons.append("Build failure")
        elif 'test' in line.lower():
            reasons.append("Test failure")
        else:
            reasons.append("General error")
    # Return the most common reason
    from collections import Counter
    most_common = Counter(reasons).most_common(1)
    return most_common[0][0] if most_common else "Unknown failure reason"

# Streamlit app
st.title("CI/CD Log Error Summarizer")

uploaded_file = st.file_uploader("Upload a CI/CD log file (.txt, .log, .pdf, .docx)", type=['txt', 'log', 'pdf', 'docx'])

if uploaded_file is not None:
    st.write(f"**File Name:** {uploaded_file.name}")
    
    # Read content
    content = read_file_content(uploaded_file)
    if content is None:
        st.error("Unsupported file type.")
    else:
        st.write("Content preview:", content[:500])
        st.write("Number of lines:", len(content.splitlines()))
        
        # Analyze file content with the shared main.py log triage logic
        entries = analyze_log_text(uploaded_file.name, content)
        st.write("Number of entries:", len(entries))
        if entries:
            st.write("First entry:", entries[0])

        if not entries:
            st.info("No actionable error details were detected in this log file.")
        else:
            failed_stage = entries[0]["failed_stage"]
            most_common_root = Counter(entry["root_cause"] for entry in entries).most_common(1)[0][0]

            st.header("CI/CD Error Triage Report")
            st.subheader("Log Summary")
            st.markdown(
                f"- **Log file:** {uploaded_file.name}\n"
                f"- **Failed stage:** {failed_stage}\n"
                f"- **Detected errors:** {len(entries)}\n"
                f"- **Most common root cause:** {most_common_root}"
            )

            st.subheader("Error Details")
            for i, entry in enumerate(entries, 1):
                st.markdown(f"### Error {i}")
                st.markdown(
                    f"- **Error type:** {entry['error_type']}\n"
                    f"- **Line number:** {entry['line_number']}\n"
                    f"- **Error snippet:** `{entry['error_snippet']}`\n"
                    f"- **Root cause:** {entry['root_cause']}\n"
                    f"- **Suggested fixes:** {entry['suggested_fixes']}\n"
                    f"- **Confidence:** {entry['confidence']:.0%}"
                )
