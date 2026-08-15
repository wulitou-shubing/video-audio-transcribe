#!/usr/bin/env python3
"""Create faithful and substitution-only calibrated spoken-script artifacts."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable, Optional


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
        # Leave the temporary file for inspection instead of deleting during
        # failure handling; some managed hosts surface deletion prompts.
        raise


def content_without_whitespace(text: str) -> str:
    return re.sub(r"\s+", "", text, flags=re.UNICODE)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


SAFE_TRADITIONAL_TO_SIMPLIFIED = str.maketrans(
    {
        "國": "国",
        "語": "语",
        "說": "说",
        "講": "讲",
        "話": "话",
        "聽": "听",
        "書": "书",
        "學": "学",
        "習": "习",
        "視": "视",
        "頻": "频",
        "號": "号",
        "個": "个",
        "們": "们",
        "這": "这",
        "樣": "样",
        "時": "时",
        "間": "间",
        "點": "点",
        "還": "还",
        "沒": "没",
        "來": "来",
        "過": "过",
        "對": "对",
        "問": "问",
        "題": "题",
        "認": "认",
        "為": "为",
        "現": "现",
        "實": "实",
        "應": "应",
        "該": "该",
        "種": "种",
        "裡": "里",
        "裏": "里",
        "開": "开",
        "關": "关",
        "門": "门",
        "網": "网",
        "頁": "页",
        "電": "电",
        "腦": "脑",
        "軟": "软",
        "體": "体",
        "標": "标",
        "內": "内",
        "轉": "转",
        "換": "换",
        "檔": "档",
        "備": "备",
        "註": "注",
        "記": "记",
        "錄": "录",
        "節": "节",
        "聲": "声",
        "資": "资",
        "訊": "讯",
        "數": "数",
        "據": "据",
        "驗": "验",
        "證": "证",
        "錯": "错",
        "別": "别",
        "簡": "简",
        "傳": "传",
        "統": "统",
        "專": "专",
        "業": "业",
        "務": "务",
        "產": "产",
        "線": "线",
        "區": "区",
        "風": "风",
        "險": "险",
        "隱": "隐",
        "權": "权",
        "測": "测",
        "試": "试",
        "際": "际",
        "羅": "罗",
        "蘇": "苏",
    }
)


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


def replacement_only(source: str, target: str) -> bool:
    source_content = content_without_whitespace(source)
    target_content = content_without_whitespace(target)
    if len(source_content) != len(target_content):
        return False
    matcher = difflib.SequenceMatcher(None, source_content, target_content, autojunk=False)
    for tag, start_a, end_a, start_b, end_b in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag != "replace" or (end_a - start_a) != (end_b - start_b):
            return False
    return True


def load_calibration_glossary(path: Optional[Path]) -> list[dict[str, str]]:
    if path is None:
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        items = [{"source": str(source), "target": str(target)} for source, target in data.items()]
    elif isinstance(data, list):
        items = []
        for index, item in enumerate(data):
            if not isinstance(item, dict) or not isinstance(item.get("source"), str) or not isinstance(item.get("target"), str):
                raise ValueError(f"glossary item {index} must contain string source and target")
            items.append({"source": item["source"], "target": item["target"]})
    else:
        raise ValueError("calibration glossary must be a JSON object or list")
    for item in items:
        source = content_without_whitespace(item["source"])
        target = content_without_whitespace(item["target"])
        if not source or not target:
            raise ValueError("calibration glossary source and target must be non-empty")
        if len(source) != len(target):
            raise ValueError(f"calibration glossary changes length: {item['source']} -> {item['target']}")
    return items


def apply_glossary(text: str, glossary: list[dict[str, str]]) -> tuple[str, list[dict[str, Any]]]:
    changes: list[dict[str, Any]] = []
    output = text
    for item in glossary:
        source = item["source"]
        target = item["target"]
        start = 0
        while True:
            index = output.find(source, start)
            if index < 0:
                break
            changes.append({"kind": "glossary", "start": index, "source": source, "target": target})
            output = output[:index] + target + output[index + len(source) :]
            start = index + len(target)
    return output, changes


def calibration_changes(source: str, target: str, limit: int = 500) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    source_index = -1
    target_index = -1
    for source_char, target_char in zip(source, target):
        if not source_char.isspace():
            source_index += 1
        if not target_char.isspace():
            target_index += 1
        if source_char != target_char and len(changes) < limit:
            changes.append(
                {
                    "source_index_ignoring_whitespace": source_index if not source_char.isspace() else None,
                    "target_index_ignoring_whitespace": target_index if not target_char.isspace() else None,
                    "source": source_char,
                    "target": target_char,
                }
            )
    return changes


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


def create_calibrated_spoken_script(
    source_path: Path,
    output_path: Path,
    report_path: Path,
    mode: str = "zh-hans",
    glossary_path: Optional[Path] = None,
) -> dict[str, Any]:
    source = source_path.read_text(encoding="utf-8")
    calibrated = source.translate(SAFE_TRADITIONAL_TO_SIMPLIFIED) if mode == "zh-hans" else source
    glossary = load_calibration_glossary(glossary_path)
    calibrated, glossary_changes = apply_glossary(calibrated, glossary)
    report = {
        "policy": "substitution-only-zero-addition-zero-deletion",
        "mode": mode,
        "glossary_path": str(glossary_path) if glossary_path else None,
        "source_character_count_ignoring_whitespace": len(content_without_whitespace(source)),
        "output_character_count_ignoring_whitespace": len(content_without_whitespace(calibrated)),
        "source_sha256": digest(content_without_whitespace(source)),
        "output_sha256": digest(content_without_whitespace(calibrated)),
        "replacement_only_ignoring_whitespace": replacement_only(source, calibrated),
        "changed_character_count": sum(1 for left, right in zip(source, calibrated) if left != right),
        "changes": calibration_changes(source, calibrated),
        "glossary_changes": glossary_changes[:200],
    }
    if not report["replacement_only_ignoring_whitespace"]:
        raise RuntimeError("calibration validation failed; calibrated script was not written")
    atomic_write_text(output_path, calibrated)
    atomic_write_text(report_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Create faithful and calibrated spoken-script artifacts")
    parser.add_argument("transcript_json", help="Transcript JSON containing a segments array")
    parser.add_argument("--output", required=True, help="Output spoken-script path")
    parser.add_argument("--report", required=True, help="Output faithfulness report path")
    parser.add_argument("--segments-per-paragraph", type=int, default=8)
    parser.add_argument("--calibrated-output", help="Optional substitution-only calibrated script path")
    parser.add_argument("--calibration-report", help="Optional calibration report path")
    parser.add_argument("--calibration-mode", choices=["none", "zh-hans"], default="none")
    parser.add_argument("--calibration-glossary", help="JSON object/list of equal-length source -> target replacements")
    args = parser.parse_args()

    data = json.loads(Path(args.transcript_json).read_text(encoding="utf-8"))
    segments = data.get("segments")
    if not isinstance(segments, list):
        raise SystemExit("transcript JSON must contain a segments array")
    report = create_spoken_script(
        segments, Path(args.output), Path(args.report), args.segments_per_paragraph
    )
    if args.calibration_mode != "none" or args.calibration_glossary:
        if not args.calibrated_output or not args.calibration_report:
            raise SystemExit("--calibrated-output and --calibration-report are required for calibration")
        report["calibration"] = create_calibrated_spoken_script(
            Path(args.output),
            Path(args.calibrated_output),
            Path(args.calibration_report),
            args.calibration_mode,
            Path(args.calibration_glossary) if args.calibration_glossary else None,
        )
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
