#!/usr/bin/env python3
"""Create a reusable isolated runtime for the skill."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
import venv
from pathlib import Path


CORE_PACKAGES = ("yt-dlp", "faster-whisper>=1.1,<2", "imageio-ffmpeg>=0.5,<1")
MIRRORS = {
    "official": "https://pypi.org/simple",
    "tsinghua": "https://pypi.tuna.tsinghua.edu.cn/simple",
    "aliyun": "https://mirrors.aliyun.com/pypi/simple/",
}


def default_runtime_dir() -> Path:
    configured = os.environ.get("VAT_RUNTIME_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return root / "video-audio-transcribe" / "runtime"
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Caches" / "video-audio-transcribe" / "runtime"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "video-audio-transcribe" / "runtime"


def runtime_python(runtime_dir: Path) -> Path:
    if os.name == "nt":
        return runtime_dir / "Scripts" / "python.exe"
    return runtime_dir / "bin" / "python"


def install(runtime_dir: Path, packages: list[str], index: str, offline: bool) -> Path:
    python = runtime_python(runtime_dir)
    if not python.exists():
        runtime_dir.parent.mkdir(parents=True, exist_ok=True)
        print(f"[setup] creating isolated runtime: {runtime_dir}", flush=True)
        venv.EnvBuilder(with_pip=True, clear=False).create(runtime_dir)

    command = [str(python), "-m", "pip", "install", "--disable-pip-version-check"]
    wheel_dir = Path(__file__).resolve().parents[1] / "vendor" / "wheels"
    if offline:
        if not wheel_dir.exists():
            raise RuntimeError(
                "offline dependency installation needs pre-downloaded wheels in vendor/wheels; "
                "see references/setup.md"
            )
        command += ["--no-index", "--find-links", str(wheel_dir)]
    elif index != "auto":
        command += ["--index-url", MIRRORS.get(index, index)]
    command += packages

    attempts = [command]
    if not offline and index == "auto" and not os.environ.get("PIP_INDEX_URL"):
        attempts.append(command[:-len(packages)] + ["--index-url", MIRRORS["tsinghua"]] + packages)

    last_error = ""
    for number, attempt in enumerate(attempts, 1):
        print(f"[setup] installing dependencies (attempt {number}/{len(attempts)})", flush=True)
        result = subprocess.run(attempt, text=True, capture_output=True)
        if result.returncode == 0:
            print("[setup] dependencies ready", flush=True)
            return python
        last_error = (result.stdout or "") + (result.stderr or "")
    raise RuntimeError("dependency installation failed:\n" + last_error[-2000:])


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare an isolated runtime")
    parser.add_argument("--runtime-dir", default=str(default_runtime_dir()))
    parser.add_argument("--pip-index", default="auto")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("packages", nargs="*", default=list(CORE_PACKAGES))
    args = parser.parse_args()
    python = install(Path(args.runtime_dir), args.packages or list(CORE_PACKAGES), args.pip_index, args.offline)
    print(python)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
