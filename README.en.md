# video-audio-transcribe

A local-first Agent Skill that turns media URLs or local audio/video into timestamped transcripts and a faithful spoken-script artifact. Spoken-script organization may change whitespace and paragraph boundaries only; it must not add, remove, or reorder transcript characters.

Current version: `v3.1.0`

[简体中文](README.md)

## Highlights

- Local MP4, MOV, MKV, MP3, M4A, WAV, SRT, and VTT input.
- Best-effort support for yt-dlp-compatible sites, with explicit boundaries for Bilibili, Douyin, Xiaohongshu, Weixin Channels, and international sites.
- Existing subtitles first, local faster-whisper fallback.
- Optional full-video download and MP3 extraction.
- URL secret redaction and private-network blocking.
- No browser-cookie access by default and no silent dependency installation in non-interactive hosts.
- Approved browser-session media handoff, target-site Cookie filtering, and resumable WorkBuddy/Windows execution.
- Installer for common Agent Skills, Codex, and WorkBuddy locations.

## Quick start

Python 3.9 or newer is required.

Clone the repository from GitHub/Gitee, or download and extract the Release ZIP. From the `video-audio-transcribe` directory, run:

```bash
python scripts/install_skill.py --host auto
python scripts/setup.py
```

The setup command presents one combined confirmation for the isolated runtime and Whisper model. In a non-interactive host, ask once and then run `python scripts/setup.py --yes`. It never reads browser cookies.

Or run directly:

```bash
python scripts/run.py "MEDIA_URL_OR_LOCAL_FILE" --output-dir transcription-output
```

Rerun an interrupted job with the same command and output directory; completed verified outputs, cached models, and partial downloads are reused.

Public access is attempted without cookies. For authenticated content, prefer an approved existing browser session that saves the media locally without exposing Cookie values. If browser handoff is unavailable, pass a site-only Netscape Cookie file with `--cookie-file`; the runner filters it into a temporary target-domain jar and deletes that copy. Direct named-browser Cookie reading is an explicitly approved, one-profile last resort and never auto-enumerates browsers.

Weixin Channels direct URLs are not promised. Export/download authorized media yourself and provide the local file. Support for every website is best effort and can change with authentication, region, and upstream extractor behavior.

The `faithfulness.json` check proves only that non-whitespace characters did not change between the transcript and `spoken-script.txt`. It does not prove that speech recognition perfectly matches the recording.

See [SECURITY.md](SECURITY.md) before reporting sensitive download failures. Licensed under the [MIT License](LICENSE).
