#!/usr/bin/env python3
"""Unified URL/local-media transcription workflow."""

from __future__ import annotations

import argparse
import html
import importlib.util
import ipaddress
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from organize_script import atomic_write_text, create_spoken_script


SKILL_DIR = Path(__file__).resolve().parents[1]
SETUP_SCRIPT = Path(__file__).with_name("setup_runtime.py")
CORE_IMPORTS = {
    "yt_dlp": "yt-dlp",
    "faster_whisper": "faster-whisper>=1.1,<2",
    "imageio_ffmpeg": "imageio-ffmpeg>=0.5,<1",
}
TIMESTAMP_RE = re.compile(
    r"(?P<h1>\d{1,2}):(?P<m1>\d{2}):(?P<s1>\d{2})[,.](?P<ms1>\d{3})\s*-->\s*"
    r"(?P<h2>\d{1,2}):(?P<m2>\d{2}):(?P<s2>\d{2})[,.](?P<ms2>\d{3})"
)
TAG_RE = re.compile(r"<[^>]+>")
URL_IN_TEXT_RE = re.compile(r"https?://[^\s<>\[\]()\"']+", re.IGNORECASE)
SENSITIVE_QUERY_RE = re.compile(
    r"(?:token|sign(?:ature)?|auth|key|secret|session|cookie|credential|password|pwd|ticket|code)",
    re.IGNORECASE,
)
PLATFORM_HOSTS = {
    "bilibili": ("bilibili.com", "b23.tv"),
    "douyin": ("douyin.com", "iesdouyin.com"),
    "xiaohongshu": ("xiaohongshu.com", "xhslink.com"),
    "weixin-channels": ("channels.weixin.qq.com",),
}


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def runtime_python(runtime_dir: Path) -> Path:
    return runtime_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def default_runtime_dir() -> Path:
    configured = os.environ.get("VAT_RUNTIME_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return root / "video-audio-transcribe" / "runtime"
    if platform.system() == "Darwin":
        return Path.home() / "Library/Caches/video-audio-transcribe/runtime"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "video-audio-transcribe/runtime"


def ensure_modules(names: list[str], args: argparse.Namespace) -> None:
    missing = [name for name in names if not module_available(name)]
    if not missing:
        return
    packages = ", ".join(CORE_IMPORTS[name] for name in missing)
    install_policy = "never" if args.no_install else args.install
    if install_policy == "never":
        raise RuntimeError(
            f"missing dependencies: {packages}. Install them manually or rerun with --install auto"
        )
    if install_policy == "ask":
        if not sys.stdin.isatty():
            raise RuntimeError(
                f"missing dependencies: {packages}. Non-interactive mode will not install software; "
                "rerun with --install auto or install them manually"
            )
        answer = input(f"Install missing dependencies into an isolated runtime ({packages})? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            raise RuntimeError("dependency installation was not approved")

    runtime_dir = Path(args.runtime_dir).expanduser().resolve()
    python = runtime_python(runtime_dir)
    current = Path(sys.executable).resolve()
    if python.exists() and current == python.resolve():
        raise RuntimeError("isolated runtime is active but dependencies are still missing")

    command = [
        sys.executable,
        str(SETUP_SCRIPT),
        "--runtime-dir",
        str(runtime_dir),
        "--pip-index",
        args.pip_index,
    ]
    if args.offline:
        command.append("--offline")
    command.extend(CORE_IMPORTS.values())
    result = subprocess.run(command)
    if result.returncode != 0:
        raise RuntimeError("automatic runtime setup failed; see references/setup.md")
    python = runtime_python(runtime_dir)
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])


def normalize_input(value: str) -> tuple[str, bool]:
    candidate = value.strip()
    embedded = URL_IN_TEXT_RE.search(candidate)
    if embedded:
        candidate = embedded.group(0).rstrip(".,;:!?。，；：！？")
    parsed = urlparse(candidate)
    if parsed.scheme in {"http", "https"}:
        if (parsed.hostname or "").lower() == "bilibili.com":
            parsed = parsed._replace(netloc="www.bilibili.com" + (f":{parsed.port}" if parsed.port else ""))
        return urlunparse(parsed), True
    if re.match(r"^(?:www\.)?[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/|$)", candidate):
        return normalize_input("https://" + candidate)
    return str(Path(candidate).expanduser().resolve()), False


def detect_platform(url: str) -> str:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if (hostname == "weixin.qq.com" or hostname.endswith(".weixin.qq.com")) and parsed.path.startswith("/sph"):
        return "weixin-channels"
    for platform_name, suffixes in PLATFORM_HOSTS.items():
        if any(hostname == suffix or hostname.endswith("." + suffix) for suffix in suffixes):
            return platform_name
    return "yt-dlp-compatible"


def redact_url(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return value
    sanitized = []
    for key, item in parse_qsl(parsed.query, keep_blank_values=True):
        looks_random = len(item) >= 32 and bool(re.search(r"[A-Za-z]", item)) and bool(re.search(r"\d", item))
        sanitized.append((key, "[REDACTED]" if SENSITIVE_QUERY_RE.search(key) or looks_random else item))
    hostname = parsed.hostname or ""
    netloc = f"[{hostname}]" if ":" in hostname else hostname
    if parsed.port:
        netloc += f":{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc, query=urlencode(sanitized)))


def sanitize_message(value: Any) -> str:
    text = str(value)
    return URL_IN_TEXT_RE.sub(lambda match: redact_url(match.group(0)) or "[REDACTED_URL]", text)


class SanitizingLogger:
    def debug(self, message: Any) -> None:
        if not str(message).startswith("[debug]"):
            print(sanitize_message(message), flush=True)

    def info(self, message: Any) -> None:
        print(sanitize_message(message), flush=True)

    def warning(self, message: Any) -> None:
        print(sanitize_message(message), file=sys.stderr, flush=True)

    def error(self, message: Any) -> None:
        print(sanitize_message(message), file=sys.stderr, flush=True)


def validate_public_url(url: str, allow_private_network: bool = False) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError("only public http/https URLs are supported")
    if allow_private_network:
        return
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise RuntimeError("local and private-network URLs are blocked; use --allow-private-network only for trusted input")
    try:
        addresses = {entry[4][0].split("%", 1)[0] for entry in socket.getaddrinfo(hostname, parsed.port or 443)}
    except socket.gaierror as error:
        raise RuntimeError(f"URL hostname could not be resolved: {hostname}: {error}") from error
    if not addresses:
        raise RuntimeError(f"URL hostname resolved to no addresses: {hostname}")
    blocked = [address for address in addresses if not ipaddress.ip_address(address).is_global]
    if blocked:
        raise RuntimeError(
            "local, private, link-local, reserved, and non-global URL targets are blocked: " + ", ".join(blocked)
        )


def browser_candidates(choice: str) -> list[Optional[str]]:
    if choice == "none":
        return [None]
    if choice != "auto":
        return [choice]
    candidates: list[Optional[str]] = [None]
    browser_paths = {
        "chrome": ["/Applications/Google Chrome.app", shutil.which("google-chrome"), shutil.which("chrome")],
        "edge": ["/Applications/Microsoft Edge.app", shutil.which("microsoft-edge")],
        "firefox": ["/Applications/Firefox.app", shutil.which("firefox")],
        "safari": ["/Applications/Safari.app"] if platform.system() == "Darwin" else [],
    }
    for browser, paths in browser_paths.items():
        if any(path and Path(path).exists() for path in paths):
            candidates.append(browser)
    return candidates


def choose_subtitle(
    info: dict[str, Any], language: str
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    requested = None if language == "auto" else language.lower()
    for kind, key in (("manual", "subtitles"), ("automatic", "automatic_captions")):
        tracks = info.get(key) or {}
        if not tracks:
            continue
        names = list(tracks)
        preferences = []
        if requested:
            preferences.extend([requested, f"ai-{requested}"])
            preferences.extend(name for name in names if requested in name.lower())
        else:
            preferences.extend(["zh-CN", "zh-Hans", "zh", "ai-zh", "en", "ai-en"])
        preferences.extend(names)
        for name in preferences:
            if name in tracks:
                inferred_kind = kind
                lowered = name.lower()
                if lowered.startswith("ai-") or "auto" in lowered:
                    inferred_kind = "automatic"
                return name, inferred_kind, key
    return None, None, None


def find_ffmpeg(args: argparse.Namespace) -> Optional[str]:
    configured = os.environ.get("FFMPEG_CMD")
    if configured and Path(configured).expanduser().is_file():
        return str(Path(configured).expanduser())
    system = shutil.which("ffmpeg")
    if system:
        return system
    ensure_modules(["imageio_ffmpeg"], args)
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def extract_mp3(source: Path, output_dir: Path, args: argparse.Namespace) -> Path:
    target_dir = output_dir / "media"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "source.mp3"
    if source.resolve() == target.resolve():
        return target
    if source.suffix.lower() == ".mp3":
        shutil.copy2(source, target)
        return target
    ffmpeg = find_ffmpeg(args)
    if not ffmpeg:
        raise RuntimeError("MP3 extraction requested but no ffmpeg implementation is available")
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        args.mp3_bitrate,
        str(target),
    ]
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0 or not target.is_file() or target.stat().st_size == 0:
        raise RuntimeError("MP3 extraction failed:\n" + (result.stderr or "")[-1500:])
    return target


def preflight_storage(output_dir: Path, min_free_space_mb: int) -> None:
    free_bytes = shutil.disk_usage(output_dir).free
    required_bytes = min_free_space_mb * 1024 * 1024
    if free_bytes < required_bytes:
        raise RuntimeError(
            f"insufficient free space: {free_bytes / 1024 / 1024:.0f} MiB available; "
            f"at least {min_free_space_mb} MiB required"
        )


def validate_duration(duration: Any, max_duration: int) -> None:
    if duration is None:
        return
    try:
        seconds = float(duration)
    except (TypeError, ValueError):
        return
    if max_duration > 0 and seconds > max_duration:
        raise RuntimeError(
            f"media duration {seconds:.0f}s exceeds the safety limit {max_duration}s; "
            "raise --max-duration explicitly if this is intentional"
        )


def validate_file_size(path: Path, max_file_size_mb: int) -> None:
    if max_file_size_mb <= 0:
        return
    size = path.stat().st_size
    limit = max_file_size_mb * 1024 * 1024
    if size > limit:
        raise RuntimeError(
            f"media file is {size / 1024 / 1024:.1f} MiB, above the {max_file_size_mb} MiB safety limit; "
            "raise --max-file-size-mb explicitly if this is intentional"
        )


def download_from_url(url: str, output_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    ensure_modules(["yt_dlp"], args)
    import yt_dlp

    cookie_attempts = [None] if args.cookie_file else browser_candidates(args.cookies)
    last_error: Optional[Exception] = None
    info: Optional[dict[str, Any]] = None
    selected_browser: Optional[str] = None

    for browser in cookie_attempts:
        options: dict[str, Any] = {
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "listsubtitles": True,
            "logger": SanitizingLogger(),
        }
        if args.cookie_file:
            options["cookiefile"] = str(Path(args.cookie_file).expanduser())
        elif browser:
            options["cookiesfrombrowser"] = (browser,)
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
            selected_browser = browser
            break
        except Exception as error:
            last_error = error
            print(
                f"[download] metadata attempt failed ({browser or 'no cookies'}): {sanitize_message(error)}",
                flush=True,
            )
    if info is None:
        raise RuntimeError(f"unable to read media metadata: {sanitize_message(last_error)}")
    validate_duration(info.get("duration"), args.max_duration)

    subtitle_path: Optional[Path] = None
    subtitle_kind: Optional[str] = None
    subtitle_language: Optional[str] = None
    subtitle_source_key: Optional[str] = None
    if not args.no_subtitles:
        subtitle_language, subtitle_kind, subtitle_source_key = choose_subtitle(info, args.language)
        if subtitle_language:
            subtitle_dir = output_dir / "source-subtitles"
            subtitle_dir.mkdir(parents=True, exist_ok=True)
            sub_options: dict[str, Any] = {
                "noplaylist": True,
                "skip_download": True,
                "writesubtitles": subtitle_source_key == "subtitles",
                "writeautomaticsub": subtitle_source_key == "automatic_captions",
                "subtitleslangs": [subtitle_language],
                "subtitlesformat": "srt/vtt/best",
                "outtmpl": str(subtitle_dir / "source.%(ext)s"),
                "quiet": True,
                "logger": SanitizingLogger(),
            }
            if args.cookie_file:
                sub_options["cookiefile"] = str(Path(args.cookie_file).expanduser())
            elif selected_browser:
                sub_options["cookiesfrombrowser"] = (selected_browser,)
            try:
                with yt_dlp.YoutubeDL(sub_options) as ydl:
                    ydl.download([url])
                candidates = sorted(
                    [p for p in subtitle_dir.glob("source.*") if p.suffix.lower() in {".srt", ".vtt"}],
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if candidates:
                    subtitle_path = candidates[0]
            except Exception as error:
                print(
                    "[subtitle] existing subtitle download failed, falling back to Whisper: "
                    + sanitize_message(error),
                    flush=True,
                )

    media_dir = output_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    selected_format = args.format
    if not selected_format:
        selected_format = "bestaudio/best" if args.download_mode == "audio" else "bestvideo*+bestaudio/best"
    media_options: dict[str, Any] = {
        "noplaylist": True,
        "format": selected_format,
        "outtmpl": str(media_dir / "source.%(ext)s"),
        "quiet": False,
        "overwrites": False,
        "continuedl": True,
        "logger": SanitizingLogger(),
    }
    if args.max_file_size_mb > 0:
        media_options["max_filesize"] = args.max_file_size_mb * 1024 * 1024
    if args.cookie_file:
        media_options["cookiefile"] = str(Path(args.cookie_file).expanduser())
    elif selected_browser:
        media_options["cookiesfrombrowser"] = (selected_browser,)
    if args.download_mode == "video":
        ffmpeg = find_ffmpeg(args)
        if ffmpeg:
            media_options["ffmpeg_location"] = ffmpeg
    with yt_dlp.YoutubeDL(media_options) as ydl:
        ydl.download([url])
    media_candidates = sorted(
        [p for p in media_dir.glob("source.*") if p.is_file() and not p.name.endswith((".part", ".ytdl"))],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not media_candidates:
        raise RuntimeError("download reported success but no media file was found")
    webpage_url = info.get("webpage_url") or url
    validate_public_url(webpage_url, args.allow_private_network)
    return {
        "media_path": media_candidates[0],
        "subtitle_path": subtitle_path,
        "subtitle_kind": subtitle_kind,
        "subtitle_source_key": subtitle_source_key,
        "subtitle_language": subtitle_language,
        "browser": selected_browser,
        "title": info.get("title"),
        "duration": info.get("duration"),
        "webpage_url": webpage_url,
    }


def timestamp_seconds(match: re.Match[str], suffix: str) -> float:
    return (
        int(match.group("h" + suffix)) * 3600
        + int(match.group("m" + suffix)) * 60
        + int(match.group("s" + suffix))
        + int(match.group("ms" + suffix)) / 1000
    )


def parse_srt_or_vtt(path: Path) -> list[dict[str, Any]]:
    content = path.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")
    blocks = re.split(r"\n\s*\n", content)
    segments: list[dict[str, Any]] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timestamp_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timestamp_index is None:
            continue
        match = TIMESTAMP_RE.search(lines[timestamp_index])
        if not match:
            continue
        text = " ".join(lines[timestamp_index + 1 :])
        text = html.unescape(TAG_RE.sub("", text)).strip()
        if text:
            segments.append(
                {"start": timestamp_seconds(match, "1"), "end": timestamp_seconds(match, "2"), "text": text}
            )
    if not segments:
        raise RuntimeError(f"no subtitle segments could be parsed from {path}")
    return segments


def endpoint_reachable(url: str) -> bool:
    try:
        request = Request(url, method="HEAD", headers={"User-Agent": "video-audio-transcribe/2"})
        with urlopen(request, timeout=5) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def configure_huggingface(args: argparse.Namespace) -> None:
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "10")
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "60")
    if args.hf_endpoint == "auto" and not os.environ.get("HF_ENDPOINT") and not args.offline:
        if endpoint_reachable("https://huggingface.co"):
            os.environ["HF_ENDPOINT"] = "https://huggingface.co"
        elif endpoint_reachable("https://hf-mirror.com"):
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    elif args.hf_endpoint == "mirror":
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    elif args.hf_endpoint not in {"auto", "official"}:
        os.environ["HF_ENDPOINT"] = args.hf_endpoint
    elif args.hf_endpoint == "official":
        os.environ.pop("HF_ENDPOINT", None)


def transcribe_media(path: Path, args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ensure_modules(["faster_whisper"], args)
    configure_huggingface(args)
    from faster_whisper import WhisperModel
    from faster_whisper.utils import download_model

    model_value = args.model_path or args.model
    device = args.device
    if device == "auto":
        try:
            import ctranslate2

            device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except Exception:
            device = "cpu"
    compute_type = args.compute_type or ("float16" if device == "cuda" else "int8")
    download_root = args.download_root or os.environ.get("WHISPER_MODEL_DIR")
    print(f"[transcribe] loading {model_value} on {device} ({compute_type})", flush=True)

    if args.model_path:
        configured_model = Path(args.model_path).expanduser().resolve()
        if not configured_model.is_dir():
            raise RuntimeError(f"model path is not a directory: {configured_model.name}")
        resolved_model = str(configured_model)
    elif args.offline or args.model_download == "never":
        try:
            resolved_model = download_model(model_value, local_files_only=True, cache_dir=download_root)
        except Exception as error:
            raise RuntimeError(
                "Whisper model is not available locally and model downloading is disabled; "
                "provide --model-path or allow a download"
            ) from error
    elif args.model_download == "auto":
        resolved_model = download_model(model_value, local_files_only=False, cache_dir=download_root)
    else:
        try:
            resolved_model = download_model(model_value, local_files_only=True, cache_dir=download_root)
        except Exception as cached_error:
            if not sys.stdin.isatty():
                raise RuntimeError(
                    "Whisper model is not cached. Non-interactive mode will not download it; "
                    "after approval rerun with --model-download auto or provide --model-path"
                ) from cached_error
            answer = input(
                f"Whisper model '{args.model}' is not cached and may be hundreds of MB. Download it? [y/N] "
            ).strip().lower()
            if answer not in {"y", "yes"}:
                raise RuntimeError("Whisper model download was not approved") from cached_error
            resolved_model = download_model(model_value, local_files_only=False, cache_dir=download_root)
    model = WhisperModel(resolved_model, device=device, compute_type=compute_type)
    kwargs: dict[str, Any] = {"beam_size": args.beam_size, "vad_filter": True}
    if args.language != "auto":
        kwargs["language"] = args.language
    raw_segments, info = model.transcribe(str(path), **kwargs)
    segments = []
    for segment in raw_segments:
        text = segment.text.strip()
        if text:
            segments.append({"start": float(segment.start), "end": float(segment.end), "text": text})
    return segments, {
        "language": info.language,
        "language_probability": float(info.language_probability),
        "duration": float(info.duration),
        "model": args.model,
        "model_path": Path(args.model_path).expanduser().name if args.model_path else None,
        "device": device,
        "compute_type": compute_type,
    }


def write_transcript_outputs(
    output_dir: Path, segments: list[dict[str, Any]], metadata: dict[str, Any], args: argparse.Namespace
) -> dict[str, Path]:
    transcript_json = output_dir / "transcript.json"
    timestamped = output_dir / "timestamped-transcript.txt"
    spoken_script = output_dir / "spoken-script.txt"
    faithfulness = output_dir / "faithfulness.json"
    metadata_path = output_dir / "metadata.json"

    transcript_data = {"segments": segments}
    atomic_write_text(transcript_json, json.dumps(transcript_data, ensure_ascii=False, indent=2) + "\n")
    lines = [f"[{s['start']:07.1f} - {s['end']:07.1f}] {s['text']}" for s in segments]
    atomic_write_text(timestamped, "\n".join(lines) + ("\n" if lines else ""))
    report = create_spoken_script(segments, spoken_script, faithfulness, args.segments_per_paragraph)
    metadata["faithfulness"] = report
    atomic_write_text(metadata_path, json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    return {
        "spoken_script": spoken_script,
        "timestamped_transcript": timestamped,
        "transcript_json": transcript_json,
        "faithfulness": faithfulness,
        "metadata": metadata_path,
    }


def doctor(args: argparse.Namespace) -> int:
    report = {
        "skill_version": (SKILL_DIR / "VERSION").read_text(encoding="utf-8").strip()
        if (SKILL_DIR / "VERSION").is_file()
        else "unknown",
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "yt_dlp": module_available("yt_dlp"),
        "faster_whisper": module_available("faster_whisper"),
        "imageio_ffmpeg": module_available("imageio_ffmpeg"),
        "ffmpeg_optional": shutil.which(os.environ.get("FFMPEG_CMD", "ffmpeg")),
        "runtime_dir": str(Path(args.runtime_dir).expanduser()),
        "network_required_for_urls": True,
        "browser_cookies_default": "none",
        "dependency_install_default": "ask",
        "model_download_default": "ask",
        "supported_input_classes": ["local-file", "yt-dlp-compatible-url"],
        "weixin_channels_direct_url": False,
        "offline_local_transcription_requires_cached_dependencies_and_model": True,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download/transcribe media and create a zero-drift spoken script")
    parser.add_argument("input", nargs="?", help="URL or local media path")
    parser.add_argument("--output-dir", default="transcription-output")
    parser.add_argument("--language", default="auto")
    parser.add_argument("--model", default="small")
    parser.add_argument("--model-path")
    parser.add_argument(
        "--model-download",
        choices=["ask", "never", "auto"],
        default="ask",
        help="Whisper model download policy (cached models are always reused)",
    )
    parser.add_argument("--download-root")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--compute-type")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--download-mode", choices=["audio", "video"], default="audio")
    parser.add_argument("--format", help="Override the yt-dlp format selector")
    parser.add_argument("--extract-mp3", action="store_true")
    parser.add_argument("--mp3-bitrate", default="192k")
    parser.add_argument(
        "--cookies",
        choices=["auto", "none", "chrome", "edge", "firefox", "safari"],
        default="none",
        help="Browser cookies are never read unless explicitly requested",
    )
    parser.add_argument("--cookie-file")
    parser.add_argument("--no-subtitles", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument(
        "--install",
        choices=["ask", "never", "auto"],
        default="ask",
        help="Dependency installation policy (default: ask; non-interactive ask never installs)",
    )
    parser.add_argument("--no-install", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--runtime-dir", default=str(default_runtime_dir()))
    parser.add_argument("--pip-index", default="auto")
    parser.add_argument("--hf-endpoint", default="auto")
    parser.add_argument("--segments-per-paragraph", type=int, default=8)
    parser.add_argument("--max-duration", type=int, default=21600, help="Maximum seconds; 0 disables the limit")
    parser.add_argument("--max-file-size-mb", type=int, default=20480, help="Maximum local/downloaded media size; 0 disables")
    parser.add_argument("--min-free-space-mb", type=int, default=1024)
    parser.add_argument(
        "--allow-private-network",
        action="store_true",
        help="Allow trusted localhost/private-network URLs (unsafe for untrusted input)",
    )
    parser.add_argument("--doctor", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.doctor:
        return doctor(args)
    if not args.input:
        parser.error("input is required unless --doctor is used")
    if args.cookie_file and args.cookies != "none":
        parser.error("choose either --cookie-file or --cookies, not both")

    started = time.time()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    preflight_storage(output_dir, args.min_free_space_mb)
    input_value, is_url = normalize_input(args.input)
    if args.offline and is_url:
        raise RuntimeError("offline mode cannot process a URL; provide a local media file")

    download: dict[str, Any] = {}
    source_path: Path
    subtitle_path: Optional[Path] = None
    if is_url:
        validate_public_url(input_value, args.allow_private_network)
        platform_name = detect_platform(input_value)
        if platform_name == "weixin-channels":
            raise RuntimeError(
                "direct Weixin Channels/视频号 URL extraction is not supported reliably; "
                "download or export the media yourself, then provide the local file"
            )
        download = download_from_url(input_value, output_dir, args)
        source_path = Path(download["media_path"])
        subtitle_path = download.get("subtitle_path")
    else:
        platform_name = "local-file"
        source_path = Path(input_value)
        if not source_path.is_file():
            raise FileNotFoundError(f"input file does not exist: {source_path}")
    validate_file_size(source_path, args.max_file_size_mb)

    if not is_url and source_path.suffix.lower() in {".srt", ".vtt"}:
        segments = parse_srt_or_vtt(source_path)
        transcript_meta = {"source": "subtitle", "subtitle_kind": "local", "language": args.language}
    elif subtitle_path:
        segments = parse_srt_or_vtt(Path(subtitle_path))
        transcript_meta = {
            "source": "subtitle",
            "subtitle_kind": download.get("subtitle_kind"),
            "subtitle_source_key": download.get("subtitle_source_key"),
            "language": download.get("subtitle_language") or args.language,
            "duration": download.get("duration"),
        }
    else:
        segments, transcript_meta = transcribe_media(source_path, args)
        transcript_meta["source"] = "whisper"

    if not segments:
        raise RuntimeError("no speech segments were produced")
    mp3_path = extract_mp3(source_path, output_dir, args) if args.extract_mp3 else None
    metadata = {
        "skill_version": (SKILL_DIR / "VERSION").read_text(encoding="utf-8").strip()
        if (SKILL_DIR / "VERSION").is_file()
        else "unknown",
        "input": redact_url(input_value) if is_url else source_path.name,
        "normalized_input": redact_url(input_value) if is_url else source_path.name,
        "is_url": is_url,
        "platform": platform_name,
        "media_path": str(source_path.relative_to(output_dir)) if is_url else source_path.name,
        "mp3_path": str(mp3_path.relative_to(output_dir)) if mp3_path else None,
        "title": download.get("title"),
        "webpage_url": redact_url(download.get("webpage_url")),
        "cookie_browser_used": download.get("browser"),
        "transcript": transcript_meta,
        "elapsed_seconds": round(time.time() - started, 3),
    }
    outputs = write_transcript_outputs(output_dir, segments, metadata, args)
    result = {"status": "ok", "outputs": {key: str(value) for key, value in outputs.items()}, "metadata": metadata}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
