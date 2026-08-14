# Setup and portability

Read this reference only when setup, restricted networking, browser cookies, host installation, or offline execution needs attention.

## Requirements

- Python 3.9 or newer.
- Network access for URL downloads.
- Network access on first use unless dependencies and a Whisper model are already cached.
- No system ffmpeg is required for transcription. For MP3 conversion or merged video downloads, the runner prefers a system ffmpeg and otherwise installs `imageio-ffmpeg` in its isolated runtime.

## Isolated runtime and installation consent

Prefer a single beginner setup that combines runtime and model consent:

```bash
python scripts/setup.py
```

In a non-interactive agent, show the complete plan once, obtain approval, then run `python scripts/setup.py --yes`. The command stores a reusable setup configuration next to the managed runtime and emits heartbeat progress while the model is prepared.

`scripts/run.py` still supports separate `--install` and `--model-download` policies for advanced automation.

After explicit approval, use:

```bash
python scripts/run.py INPUT --install auto
```

Use `--install never` when the environment is centrally managed.

Override the location with:

```bash
VAT_RUNTIME_DIR=/custom/cache/runtime python scripts/run.py INPUT
```

Select a package index when PyPI is inaccessible:

```bash
python scripts/run.py INPUT --pip-index tsinghua
python scripts/run.py INPUT --pip-index aliyun
python scripts/run.py INPUT --pip-index https://example.com/simple
```

The `PIP_INDEX_URL` environment variable is also honored.

## Hugging Face and Whisper models

Cached models are reused automatically. The default `--model-download ask` requests confirmation before an uncached model is downloaded. In a non-interactive host, obtain explicit approval and pass `--model-download auto`, or use `--model-path`. Use `--model-download never` to require an existing cache.

Use the official endpoint by default or select a mirror:

```bash
python scripts/run.py INPUT --hf-endpoint official
python scripts/run.py INPUT --hf-endpoint mirror
python scripts/run.py INPUT --hf-endpoint https://your-mirror.example.com
```

Use a pre-downloaded CTranslate2/faster-whisper model without network access:

```bash
python scripts/run.py LOCAL_MEDIA --offline --model-path /path/to/model
```

`WHISPER_MODEL_DIR` sets the model cache directory. `HF_ENDPOINT` remains authoritative when already set and `--hf-endpoint auto` is used.

For a fully offline machine, use the same version with a compatible wheel directory and a local CTranslate2 model:

```bash
python scripts/setup.py --offline --wheel-dir /path/to/wheels --model-path /path/to/model
```

Do not commit large wheels or model files to Git unless the repository owner has intentionally chosen that distribution strategy and verified licenses.

## Cookies and authentication

The default `--cookies none` never reads a browser profile. On `AUTH_REQUIRED`, prefer a supported host browser tool after one consolidated approval: open only the target page, save/download the media to the local job directory, and process that local file. Do not inspect cookies, local storage, passwords, or session stores.

If browser handoff is unavailable, export a target-site Netscape Cookie file:

```bash
python scripts/run.py URL --cookie-file /path/to/site-only-cookies.txt
```

The runner filters it into a temporary Cookie jar containing only domains associated with the target platform, applies restrictive permissions where supported, and removes the temporary copy after the attempt. The original user file is never modified.

Direct browser-profile access is an advanced last resort after explicit approval for one named profile:

```bash
python scripts/run.py URL --cookies chrome
```

Try a named profile once. Never use `auto`, enumerate browsers, or cycle through Chrome/Edge/Firefox. Never commit Cookie files. Only download media the user is authorized to access and follow the source site's terms.

## GitHub and non-GitHub distribution

Run `python scripts/install_skill.py --host auto` from the downloaded repository. It detects common Codex/Agent Skills and WorkBuddy locations. Use `--host all` to install to every common host, or choose `agents`, `codex`, or `workbuddy` explicitly. Existing installations are not overwritten unless `--force` is supplied.

For users who cannot reach GitHub, publish the same release archive through an accessible mirror such as Gitee or an approved file host. A mirror cannot eliminate the source website's own network or authentication requirements.

## Troubleshooting

Run:

```bash
python scripts/run.py --doctor
```

Common interpretations:

- Missing Python dependency: allow automatic setup or select a reachable package index.
- `AUTH_REQUIRED`: use an approved browser media handoff, a target-site Cookie file, or local media.
- `UNSUPPORTED_URL` / `BROWSER_HANDOFF_REQUIRED`: use browser handoff or local media; do not improvise undocumented APIs.
- `DOWNLOAD_INCOMPLETE`: rerun the same command and output directory.
- Local offline transcription fails: supply `--model-path` and ensure dependencies are cached.
- Site format failure: keep the default `bestaudio/best` for transcription; request full video only when required.
- `faithfulness.json` is false or missing: do not deliver `spoken-script.txt` as a faithful output.
