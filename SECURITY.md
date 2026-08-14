# Security policy

## Reporting a vulnerability

Use GitHub's private vulnerability reporting feature when it is enabled. If it is unavailable, open a minimal issue asking the maintainer for a private contact channel; do not publish exploit details or sensitive artifacts.

Never attach browser cookie files, authorization headers, unredacted signed URLs, private media, full debug logs, or transcripts containing personal data to a public issue. Replace secrets with `[REDACTED]` and provide only the smallest reproducible example.

## Security model

- Browser cookies are opt-in.
- Dependency and uncached-model downloads are confirm-first; non-interactive execution does not download them by default.
- Local, private, link-local, reserved, and other non-global URL targets are blocked unless a trusted user explicitly passes `--allow-private-network`.
- Common token/signature URL parameters are redacted from generated metadata and yt-dlp logger output.
- The project does not bypass CAPTCHA, paywalls, DRM, login controls, rate limits, or other access controls.

Secret redaction is defense in depth, not a guarantee. Review every artifact before sharing it.
