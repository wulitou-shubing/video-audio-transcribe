# video-audio-transcribe

A local-first Agent Skill that turns media URLs or local audio/video into timestamped transcripts and a faithful spoken-script artifact. Spoken-script organization may change whitespace and paragraph boundaries only; it must not add, remove, or reorder transcript characters.

[简体中文](README.md)

## Highlights

- Local MP4, MOV, MKV, MP3, M4A, WAV, SRT, and VTT input.
- Best-effort support for yt-dlp-compatible sites, with explicit boundaries for Bilibili, Douyin, Xiaohongshu, Weixin Channels, and international sites.
- Existing subtitles first, local faster-whisper fallback.
- Optional full-video download and MP3 extraction.
- URL secret redaction and private-network blocking.
- No browser-cookie access by default and no silent dependency installation in non-interactive hosts.
- Installer for common Agent Skills, Codex, and WorkBuddy locations.

## Quick start

Python 3.9 or newer is required.

Clone the repository from GitHub/Gitee, or download and extract the Release ZIP. From the `video-audio-transcribe` directory, run:

```bash
python scripts/install_skill.py --host auto
```

Or run directly:

```bash
python scripts/run.py "MEDIA_URL_OR_LOCAL_FILE" --output-dir transcription-output
```

Missing dependencies and uncached Whisper models are downloaded only after separate interactive confirmations. After explicit approval in a non-interactive host, pass `--install auto` and/or `--model-download auto`. Browser cookies default to `none`; use a named browser or cookie file only with explicit approval.

Weixin Channels direct URLs are not promised. Export/download authorized media yourself and provide the local file. Support for every website is best effort and can change with authentication, region, and upstream extractor behavior.

The `faithfulness.json` check proves only that non-whitespace characters did not change between the transcript and `spoken-script.txt`. It does not prove that speech recognition perfectly matches the recording.

See [SECURITY.md](SECURITY.md) before reporting sensitive download failures. Licensed under the [MIT License](LICENSE).
