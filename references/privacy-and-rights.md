# Privacy, authentication, and rights

Read this reference before using cookies, processing confidential recordings, publishing logs, or diagnosing protected media.

- Process only media the user is authorized to access and download. Follow applicable laws and the source site's terms.
- Do not bypass CAPTCHA, login requirements, rate limits, paywalls, DRM, geographic controls, or other access controls.
- Never inspect a browser cookie database without explicit approval. Prefer `--cookies none`; use a named browser or cookie file only for the requested URL and only after approval.
- Never print, copy, upload, commit, or retain cookie values. Store cookie files outside the repository and delete user-managed exports when the user requests it.
- Treat source media, transcripts, titles, filenames, and speakers as potentially sensitive personal data.
- The runner redacts common secret-bearing URL parameters in metadata and logs, but users must still review artifacts before publishing an issue.
- Keep private-network URL protection enabled for untrusted input. `--allow-private-network` is only for an explicitly trusted internal source.
- Do not upload source media or transcripts to a cloud service unless the user has authorized that specific transfer.
- A successful transcript-to-script hash proves only that the organizing step did not add or remove non-whitespace characters. It does not prove speech-recognition accuracy.
