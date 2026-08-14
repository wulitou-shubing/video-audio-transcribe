#!/usr/bin/env python3
"""Create a whitespace-only reformatted spoken script and prove zero content drift."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def content_without_whitespace(text: str) -> str:
    return re.sub(r"\s+", "", text, flags=re.UNICODE)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def segment_texts(segments: Iterable[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for index, segment in enumerate(segments):
        value = segment.get("text")
        if not isinstance(value, str):
            raise ValueError(f"segment {index} has no string text")
        # Strip boundary whitespace only. Never change internal characters.
        value = value.strip()
        if value:
            values.append(value)
    return values


def format_paragraphs(texts: list[str], segments_per_paragraph: int) -> str:
    if segments_per_paragraph < 1:
        raise ValueError("segments_per_paragraph must be at least 1")
    paragraphs = []
    for start in range(0, len(texts), segments_per_paragraph):
        # Newlines are the only inserted characters and are ignored by validation.
        paragraphs.append("\n".join(texts[start : start + segments_per_paragraph]))
    return "\n\n".join(paragraphs) + ("\n" if paragraphs else "")


def create_spoken_script(
    segments: list[dict[str, Any]], output_path: Path, report_path: Path, segments_per_paragraph: int = 8
) -> dict[str, Any]:
    texts = segment_texts(segments)
    source_content = content_without_whitespace("".join(texts))
    output = format_paragraphs(texts, segments_per_paragraph)
    output_content = content_without_whitespace(output)
    report = {
        "policy": "zero-addition-zero-deletion-ignoring-whitespace",
        "source_segment_count": len(texts),
        "source_character_count_ignoring_whitespace": len(source_content),
        "output_character_count_ignoring_whitespace": len(output_content),
        "source_sha256": digest(source_content),
        "output_sha256": digest(output_content),
        "exact_match_ignoring_whitespace": source_content == output_content,
    }
    if not report["exact_match_ignoring_whitespace"]:
        raise RuntimeError("faithfulness validation failed; spoken script was not written")
    atomic_write_text(output_path, output)
    atomic_write_text(report_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a zero-addition, zero-deletion spoken script")
    parser.add_argument("transcript_json", help="Transcript JSON containing a segments array")
    parser.add_argument("--output", required=True, help="Output spoken-script path")
    parser.add_argument("--report", required=True, help="Output faithfulness report path")
    parser.add_argument("--segments-per-paragraph", type=int, default=8)
    args = parser.parse_args()

    data = json.loads(Path(args.transcript_json).read_text(encoding="utf-8"))
    segments = data.get("segments")
    if not isinstance(segments, list):
        raise SystemExit("transcript JSON must contain a segments array")
    report = create_spoken_script(
        segments, Path(args.output), Path(args.report), args.segments_per_paragraph
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
