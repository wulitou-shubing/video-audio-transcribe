#!/usr/bin/env python3
"""Build a portable release ZIP and SHA-256 checksum."""

from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFIX = ROOT.name
TOP_FILES = (
    ".gitignore",
    "LICENSE",
    "README.md",
    "README.en.md",
    "SECURITY.md",
    "SKILL.md",
    "VERSION",
    "requirements.txt",
)
TOP_DIRS = ("agents", "references", "scripts")


def release_files() -> list[Path]:
    files = [ROOT / name for name in TOP_FILES]
    for directory in TOP_DIRS:
        files.extend(path for path in (ROOT / directory).rglob("*") if path.is_file())
    return sorted(
        path
        for path in files
        if "__pycache__" not in path.parts and path.suffix not in {".pyc", ".part"}
    )


def build(output: Path) -> tuple[Path, Path]:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in release_files():
            archive.write(path, Path(PREFIX) / path.relative_to(ROOT))
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    checksum_path = output.with_suffix(output.suffix + ".sha256")
    checksum_path.write_text(f"{checksum}  {output.name}\n", encoding="utf-8")
    return output, checksum_path


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    parser = argparse.ArgumentParser(description="Build release ZIP and checksum")
    parser.add_argument("--output", default=str(ROOT.parent / f"{PREFIX}-v{version}.zip"))
    args = parser.parse_args()
    archive, checksum = build(Path(args.output).expanduser().resolve())
    print(archive)
    print(checksum)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
