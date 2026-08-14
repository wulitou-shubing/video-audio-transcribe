# Platform capability boundaries

Read this reference before promising that a site is supported.

| Input | Support level | Notes |
| --- | --- | --- |
| Local video/audio/subtitle | First-class | Works offline after dependencies and a Whisper model are cached. |
| Bilibili | Adapted, best effort | Dedicated yt-dlp extractor; subtitles, login-only formats, multipart videos, and 403 responses vary. |
| Douyin | Adapted, best effort | Site changes and fresh sessions can require explicitly approved cookies. |
| Xiaohongshu | Adapted, best effort | Share links, session state, and anti-bot changes can affect downloads. |
| Weixin Channels / 视频号 URL | No reliable direct extractor | Ask the user to export/download the media and provide a local file. Do not bypass access controls. |
| YouTube and other international sites | yt-dlp-compatible, best effort | Availability varies by region, authentication, extractor health, and site changes. |

“Listed by yt-dlp” does not guarantee that every URL works forever. Report the actual result, source, authentication mode, and fallback. Never describe the skill as guaranteed to support every platform.

The runner accepts ordinary URLs, URLs without a scheme, and share text containing an `http://` or `https://` URL. It processes one media item at a time and refuses playlists/live-stream workflows unless a future version implements them explicitly.

If a public attempt returns an authentication or unsupported-extractor error, do not explore arbitrary fallback APIs. Prefer a user-approved browser session that saves the media locally; otherwise request a site-scoped Cookie export or local media file.
