#!/usr/bin/env python3
"""Install this skill into common Agent Skills hosts without bundling runtime data."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


SKILL_NAME = "video-audio-transcribe"
SKILL_ROOT = Path(__file__).resolve().parents[1]
INCLUDED_FILES = ("SKILL.md", "requirements.txt", ".gitignore", "VERSION")
INCLUDED_DIRS = ("agents", "scripts", "references")


def host_roots() -> dict[str, Path]:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    return {
        "agents": Path.home() / ".agents" / "skills",
        "codex": codex_home / "skills",
        "workbuddy": Path.home() / ".workbuddy" / "skills",
    }


def select_roots(host: str) -> list[Path]:
    roots = host_roots()
    if host == "all":
        return list(roots.values())
    if host != "auto":
        return [roots[host]]
    for name in ("workbuddy", "codex", "agents"):
        if roots[name].parent.exists():
            return [roots[name]]
    return [roots["agents"]]


def install_one(skills_root: Path, force: bool) -> Path:
    destination = skills_root / SKILL_NAME
    destination.mkdir(parents=True, exist_ok=True)
    for name in INCLUDED_FILES:
        source = SKILL_ROOT / name
        if source.exists():
            shutil.copy2(source, destination / name)
    for name in INCLUDED_DIRS:
        shutil.copytree(
            SKILL_ROOT / name,
            destination / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            dirs_exist_ok=True,
        )
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Install video-audio-transcribe for Codex/Agent Skills/WorkBuddy")
    parser.add_argument("--host", choices=["auto", "agents", "codex", "workbuddy", "all"], default="auto")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Deprecated compatibility flag; updates managed files in place and never removes the skill folder",
    )
    args = parser.parse_args()

    destinations = []
    for root in select_roots(args.host):
        destinations.append(install_one(root, args.force))
    for destination in destinations:
        print(destination)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"error: {error}")
        raise SystemExit(1)
