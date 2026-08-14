---
name: video-audio-transcribe
description: Download online video or audio from yt-dlp-compatible sites, process local media, reuse available subtitles, transcribe speech with faster-whisper, and produce timestamped transcripts plus a strictly faithful spoken-script version with zero added or removed transcript characters. Use for video-to-text, audio-to-text, subtitle extraction, MP3/audio extraction, Douyin/Xiaohongshu/Bilibili and other compatible links, locally exported Weixin Channels/视频号 media, local MP4/MOV/MKV/MP3/M4A/WAV files, or requests for 口播文案、逐字稿、字幕、语音转写. Do not use the faithful-script output for summarization or rewriting.
---

# Video Audio Transcribe

Turn a URL or local media file into resumable transcript artifacts with one command. Keep this workflow deterministic; do not improvise undocumented download or anti-bot methods.

## Prepare once

On first use, present one combined confirmation covering the isolated runtime and the Whisper model. After approval, run in the foreground:

```bash
python scripts/setup.py --yes
```

This setup never reads browser cookies. It reuses caches, selects the official or mirror model endpoint, keeps the parent process alive on Windows/WorkBuddy, and emits short progress heartbeats. For a fully offline machine, use `--offline --wheel-dir WHEELS --model-path MODEL_DIR` with the same script.

## Run the workflow

Use the unified entry point:

```bash
python scripts/run.py INPUT --output-dir OUTPUT_DIR
```

The script must:

1. Normalize a URL that omits `https://`.
2. Prefer an existing subtitle track when available.
3. Otherwise download the best available audio and transcribe it locally.
4. For local media, transcribe the file directly; do not require ffmpeg.
5. Write `transcript.json`, `timestamped-transcript.txt`, `spoken-script.txt`, `faithfulness.json`, and `metadata.json`.
6. Verify that `spoken-script.txt` contains exactly the transcript characters in the same order after whitespace is ignored.

Use `--download-mode video` when the user explicitly requests the full video. Use `--extract-mp3` when the user explicitly requests MP3 output. The runner uses a system ffmpeg when present and can fall back to the `imageio-ffmpeg` bundled binary.

Use `--doctor` first only when setup is uncertain:

```bash
python scripts/run.py --doctor
```

Prefer the one-time setup command instead of answering separate dependency and model questions during a job. If a job is interrupted, rerun exactly the same command and output directory; verified outputs and partial downloads are reused by default. Never move a normal job into an untracked background process.

## Preserve spoken content exactly

Treat `spoken-script.txt` as a zero-addition, zero-deletion artifact.

- Never summarize, polish, rewrite, reorder, complete, infer, title, introduce, conclude, or fact-check inside this file.
- Never remove fillers, repetitions, false starts, advertisements, calls to action, or disclaimers.
- Never add headings, speaker labels, editorial notes, punctuation, or words that are absent from the transcript.
- Only remove timestamps and change whitespace or paragraph boundaries.
- Keep suspected recognition errors unchanged. Record concerns separately in the final response; do not silently repair them.
- Require `faithfulness.json` to report `exact_match_ignoring_whitespace: true` before delivery.

This validation proves that no content changed between `transcript.json` and `spoken-script.txt`. It cannot prove that speech recognition perfectly matches the original audio. Preserve the timestamped transcript and source media so uncertain recognition can be reviewed.

If the user requests rewriting or summarization, create a separate clearly named file and preserve the faithful files unchanged. A rewritten file is not the faithful spoken script.

## Choose sources

- Prefer manually authored subtitles over automatic subtitles.
- Prefer subtitles matching `--language`; otherwise use Whisper.
- Use `--no-subtitles` to force Whisper.
- Start every URL with one public, no-cookie attempt.
- Never enumerate browsers, inspect cookie databases, local storage, passwords, or session stores automatically.
- When one or more URLs return `AUTH_REQUIRED` or `BROWSER_HANDOFF_REQUIRED`, consolidate them into one user-facing decision.
- Prefer an explicitly approved existing browser session: open only the target URLs with a supported host browser tool, save/download the media to the local job directory, then run this script on the local files. Never extract or display Cookie values during browser handoff.
- If browser handoff is unavailable, accept a user-exported Netscape Cookie file with `--cookie-file PATH`. The runner copies only cookies matching the target platform into a permission-restricted temporary file and deletes that copy after the attempt.
- Use `--cookies chrome` (or one other named browser) only as an advanced last resort after explicit approval for that single profile. Try it once; never cycle through installed browsers.
- If the approved route fails, request a locally exported media file. Do not try undocumented APIs, signature generation, headless-browser bypasses, CAPTCHA workarounds, or unrelated skills.
- For URL transcription, download audio by default. Only download full video when the user explicitly asks for it.

Treat structured errors as terminal routing signals:

- `AUTH_REQUIRED`: ask once for browser media handoff; otherwise request a site-scoped Cookie file or local media.
- `BROWSER_HANDOFF_REQUIRED` / `UNSUPPORTED_URL`: use an approved browser session or local media.
- `DOWNLOAD_INCOMPLETE`: rerun the same command and output directory.
- `MODEL_UNAVAILABLE`: retry the mirror once or use a local/offline model.

## Work with restricted or offline environments

- A URL always requires access to the source website.
- Local-file transcription can run offline after dependencies and a Whisper model are cached.
- Use `--offline --model-path LOCAL_MODEL_DIR` for fully offline transcription.
- Honor `VAT_RUNTIME_DIR`, `HF_ENDPOINT`, `PIP_INDEX_URL`, `YTDLP_CMD`, and `WHISPER_MODEL_DIR` when set.
- Never claim success if a download, dependency installation, model load, transcript write, or faithfulness check failed.
- Treat URL input as untrusted. Keep private-network blocking enabled unless the user explicitly supplies a trusted internal URL.
- Do not bypass CAPTCHA, login, rate limits, paywalls, DRM, or access controls. Stop and ask for a lawful local file when needed.

Read [references/platforms.md](references/platforms.md) before making platform-support claims. Read [references/privacy-and-rights.md](references/privacy-and-rights.md) before using cookies, handling sensitive media, or publishing logs.

## Deliver results

Report the selected source (`subtitle` or `whisper`), duration when known, language, model when used, and output files. Present `spoken-script.txt` first, followed by the timestamped transcript and media file.
