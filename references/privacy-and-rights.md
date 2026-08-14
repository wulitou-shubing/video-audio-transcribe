# Privacy, authentication, and rights

Read this reference before using cookies, processing confidential recordings, publishing logs, or diagnosing protected media.

- Process only media the user is authorized to access and download. Follow applicable laws and the source site's terms.
- Do not bypass CAPTCHA, login requirements, rate limits, paywalls, DRM, geographic controls, or other access controls.
- Never enumerate or inspect browser cookie databases automatically. Prefer an approved browser-session media handoff that returns a local file without exposing Cookie values.
- If a Cookie file is necessary, ask the user to export only the target site. The runner filters it into a target-domain temporary jar, uses restrictive permissions, and deletes the temporary copy.
- Use a named browser profile only as an explicitly approved, single-profile last resort. Never cycle across installed browsers.
- Never print, copy, upload, commit, or retain cookie values. Store cookie files outside the repository and delete user-managed exports when the user requests it.
- Treat source media, transcripts, titles, filenames, and speakers as potentially sensitive personal data.
- The runner redacts common secret-bearing URL parameters in metadata and logs, but users must still review artifacts before publishing an issue.
- Keep private-network URL protection enabled for untrusted input. `--allow-private-network` is only for an explicitly trusted internal source.
- Do not upload source media or transcripts to a cloud service unless the user has authorized that specific transfer.
- Do not use undocumented anti-bot APIs, signature generation, headless-browser workarounds, or CAPTCHA bypasses.
- A successful transcript-to-script hash proves only that the organizing step did not add or remove non-whitespace characters. It does not prove speech-recognition accuracy.
