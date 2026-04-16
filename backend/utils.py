"""
Utility functions for log file reading, chunking, and classification.
"""

import os
import re


def read_log_file(filepath: str) -> str:
    """Read and return the contents of a log file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Log file not found: {filepath}")
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def chunk_log(content: str, max_chars: int = 200) -> list[str]:
    """
    Split log content into chunks of approximately max_chars characters.
    Splits by lines first, then merges consecutive lines into chunks.
    """
    lines = content.strip().split("\n")
    chunks = []
    current_chunk = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # If adding this line would exceed max_chars, finalize the current chunk
        if current_chunk and len(current_chunk) + len(line) + 1 > max_chars:
            chunks.append(current_chunk)
            current_chunk = line
        else:
            if current_chunk:
                current_chunk += "\n" + line
            else:
                current_chunk = line

    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def classify_line(line: str) -> str:
    """Classify a log line as ERROR, WARNING, or INFO."""
    line_upper = line.upper()
    if re.search(r"\[?\s*ERROR\s*\]?", line_upper):
        return "ERROR"
    elif re.search(r"\[?\s*WARNING\s*\]?", line_upper) or re.search(r"\[?\s*WARN\s*\]?", line_upper):
        return "WARNING"
    return "INFO"


def get_log_stats(content: str) -> dict:
    """Count ERROR, WARNING, and INFO lines in log content."""
    lines = content.strip().split("\n")
    stats = {"total_lines": len(lines), "error": 0, "warning": 0, "info": 0}

    for line in lines:
        level = classify_line(line)
        if level == "ERROR":
            stats["error"] += 1
        elif level == "WARNING":
            stats["warning"] += 1
        else:
            stats["info"] += 1

    return stats
