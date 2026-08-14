# Setup and portability

Read this reference only when setup, restricted networking, browser cookies, host installation, or offline execution needs attention.

## Requirements

- Python 3.9 or newer.
- Network access for URL downloads.
- Network access on first use unless dependencies and a Whisper model are already cached.
- No system ffmpeg is required for transcription. For MP3 conversion or merged video downloads, the runner prefers a system ffmpeg and otherwise installs `imageio-ffmpeg` in its isolated runtime.

## Isolated runtime and installation consent

`scripts/run.py` reuses installed packages when possible. The default `--install ask` asks before it creates an isolated environment and installs packages. In a non-interactive agent it stops instead of installing silently.

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

For fully offline dependency installation, place compatible wheels in `vendor/wheels`, then run with `--offline`. Do not commit large wheels or model files to Git unless the repository owner has intentionally chosen that distribution strategy and verified licenses.

## Cookies and authentication

The default `--cookies none` never reads a browser profile. Reading browser cookies can expose sessions for unrelated websites, so obtain explicit approval first.

Choose a browser explicitly:

```bash
python scripts/run.py URL --cookies chrome
python scripts/run.py URL --cookies edge
python scripts/run.py URL --cookies firefox
```

When browser cookie decryption is blocked, export a Netscape-format cookie file and use:

```bash
python scripts/run.py URL --cookie-file /path/to/cookies.txt
```

Never commit cookie files. Only download media the user is authorized to access and follow the source site's terms.

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
- URL fails without cookies: use an installed browser or `--cookie-file`.
- Local offline transcription fails: supply `--model-path` and ensure dependencies are cached.
- Site format failure: keep the default `bestaudio/best` for transcription; request full video only when required.
- `faithfulness.json` is false or missing: do not deliver `spoken-script.txt` as a faithful output.
