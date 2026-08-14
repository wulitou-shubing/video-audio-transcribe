#!/usr/bin/env python3
"""One-prompt beginner setup for the managed runtime and Whisper model."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen

from setup_runtime import CORE_PACKAGES, default_runtime_dir, install


def reachable(url: str, timeout: float) -> bool:
    try:
        request = Request(url, method="HEAD", headers={"User-Agent": "video-audio-transcribe/3.1"})
        with urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def choose_endpoint(value: str, timeout: float) -> str:
    if value == "official":
        return "https://huggingface.co"
    if value == "mirror":
        return "https://hf-mirror.com"
    if value != "auto":
        return value
    for endpoint in ("https://huggingface.co", "https://hf-mirror.com"):
        print(json.dumps({"event": "setup", "stage": "endpoint", "checking": endpoint}), flush=True)
        if reachable(endpoint, timeout):
            return endpoint
    raise RuntimeError(
        "no model endpoint is reachable; use --hf-endpoint URL, or use --offline with a local model/cache"
    )


def prepare_model(
    python: Path,
    model: str,
    model_path: Optional[str],
    download_root: Path,
    endpoint: Optional[str],
    offline: bool,
    progress_interval: float,
) -> str:
    if model_path:
        path = Path(model_path).expanduser().resolve()
        if not path.is_dir():
            raise RuntimeError(f"model path is not a directory: {path}")
        return str(path)
    environment = os.environ.copy()
    environment["VAT_SETUP_MODEL"] = model
    environment["VAT_SETUP_MODEL_ROOT"] = str(download_root)
    environment["VAT_SETUP_OFFLINE"] = "1" if offline else "0"
    environment.setdefault("HF_HUB_DISABLE_XET", "1")
    environment.setdefault("HF_HUB_ETAG_TIMEOUT", "30")
    environment.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "300")
    if endpoint:
        environment["HF_ENDPOINT"] = endpoint
    code = (
        "import os; from faster_whisper.utils import download_model; "
        "print(download_model(os.environ['VAT_SETUP_MODEL'], "
        "cache_dir=os.environ['VAT_SETUP_MODEL_ROOT'], "
        "local_files_only=os.environ['VAT_SETUP_OFFLINE']=='1'))"
    )
    print(json.dumps({"event": "setup", "stage": "model", "status": "running"}), flush=True)
    process = subprocess.Popen([str(python), "-c", code], env=environment)
    started = time.monotonic()
    while True:
        try:
            process.wait(timeout=max(1.0, progress_interval))
            break
        except subprocess.TimeoutExpired:
            print(
                json.dumps(
                    {
                        "event": "setup",
                        "stage": "model",
                        "status": "running",
                        "elapsed_seconds": round(time.monotonic() - started),
                    }
                ),
                flush=True,
            )
    if process.returncode != 0:
        raise RuntimeError("model preparation failed; rerun to resume or provide --model-path")
    return model


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare video-audio-transcribe with one confirmation")
    parser.add_argument("--yes", action="store_true", help="Use after the user approved the complete setup plan")
    parser.add_argument("--runtime-dir", default=str(default_runtime_dir()))
    parser.add_argument("--model", default="small")
    parser.add_argument("--model-path")
    parser.add_argument("--download-root")
    parser.add_argument("--pip-index", default="auto")
    parser.add_argument("--hf-endpoint", default="auto")
    parser.add_argument("--endpoint-timeout", type=float, default=15.0)
    parser.add_argument("--progress-interval", type=float, default=10.0)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--wheel-dir")
    args = parser.parse_args()

    if not args.yes:
        if not sys.stdin.isatty():
            raise RuntimeError("setup needs one confirmation; rerun with --yes after user approval")
        answer = input(
            "Create an isolated runtime and prepare a Whisper model (may download hundreds of MB; "
            "never reads browser cookies)? [y/N] "
        ).strip().lower()
        if answer not in {"y", "yes"}:
            raise RuntimeError("setup was not approved")

    runtime_dir = Path(args.runtime_dir).expanduser().resolve()
    wheel_dir = Path(args.wheel_dir).expanduser().resolve() if args.wheel_dir else None
    if args.offline and not wheel_dir and not (Path(__file__).resolve().parents[1] / "vendor" / "wheels").exists():
        raise RuntimeError("offline setup requires --wheel-dir or bundled vendor/wheels")
    print(json.dumps({"event": "setup", "stage": "runtime", "status": "running"}), flush=True)
    python = install(runtime_dir, list(CORE_PACKAGES), args.pip_index, args.offline, wheel_dir)

    endpoint = None if args.offline else choose_endpoint(args.hf_endpoint, args.endpoint_timeout)
    model_root = (
        Path(args.download_root).expanduser().resolve()
        if args.download_root
        else runtime_dir.parent / "models"
    )
    model_root.mkdir(parents=True, exist_ok=True)
    model_value = prepare_model(
        python,
        args.model,
        args.model_path,
        model_root,
        endpoint,
        args.offline,
        args.progress_interval,
    )
    config = {
        "runtime_dir": str(runtime_dir),
        "model": args.model,
        "model_path": str(Path(args.model_path).expanduser().resolve()) if args.model_path else None,
        "download_root": str(model_root),
        "hf_endpoint": endpoint,
        "browser_cookies": "never_automatic",
    }
    config_path = runtime_dir.parent / "setup.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"status": "ok", "runtime_python": str(python), "model": model_value, "config": str(config_path)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(json.dumps({"status": "error", "message": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
