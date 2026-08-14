# video-audio-transcribe

一个本地优先的 Agent Skill：从视频链接或本地音视频生成带时间戳的逐字稿和口播文案。口播整理只能改变空白与分段，不允许增加、删除或调换转写字符。

[English](README.en.md)

## 功能

- 处理本地 MP4、MOV、MKV、MP3、M4A、WAV、SRT 和 VTT。
- 处理 yt-dlp 兼容的国内外网站，已针对 B 站、抖音和小红书设置清晰的失败与 Cookie 回退路径。
- 优先复用平台字幕，否则用 faster-whisper 本地转写。
- 可选下载完整视频或提取 MP3。
- 自动脱敏 URL 中常见的 token/签名参数，默认拦截本机和私网 URL。
- 默认不读取浏览器 Cookie，也不在非交互环境中静默安装依赖。
- 兼容 Codex、通用 Agent Skills 目录和 WorkBuddy。

## 快速开始

需要 Python 3.9 或更高版本。

从 GitHub/Gitee 克隆仓库，或下载 Release ZIP 并解压。进入 `video-audio-transcribe` 目录后运行：

```bash
python scripts/install_skill.py --host auto
```

`--host auto` 会检测已存在的 Agent Skills/Codex/WorkBuddy 目录；也可显式使用 `agents`、`codex`、`workbuddy` 或 `all`。安装器不会覆盖已存在的 Skill，除非传入 `--force`。

也可不安装，直接在仓库中运行：

```bash
python scripts/run.py "视频链接或本地文件" --output-dir transcription-output
```

第一次缺少依赖或 Whisper 模型时，交互式终端会分别询问是否下载。在 WorkBuddy 等非交互宿主中，先征得用户同意，再运行：

```bash
python scripts/run.py INPUT --install auto --model-download auto
```

## Cookie 与登录

默认 `--cookies none`。公开内容失败且用户明确同意后，才使用：

```bash
python scripts/run.py URL --cookies chrome
python scripts/run.py URL --cookie-file /path/to/cookies.txt
```

不要提交 Cookie 文件，不要将包含登录凭证的日志粘贴到 Issue。

## 平台边界

| 平台/输入 | 能力 |
| --- | --- |
| 本地文件 | 一级支持；缓存模型和依赖后可离线运行 |
| B 站 | 已适配，实际可用性受会员格式、分 P、地区和站点变更影响 |
| 抖音 | 已适配，部分链接需要新鲜会话 |
| 小红书 | 已适配，分享链接和反机器人策略可能变化 |
| 视频号 | 不承诺直链下载；支持用户合法导出后的本地文件 |
| YouTube 等其他站点 | yt-dlp 兼容范围内尽力支持，不保证永久可用 |

## 输出与保真性

- `spoken-script.txt`：只改变空白的口播文案。
- `timestamped-transcript.txt`：带时间戳文字稿。
- `transcript.json`：结构化分段。
- `faithfulness.json`：去除空白后的字符数、SHA-256 和精确匹配结果。
- `metadata.json`：来源、语言、字幕类型、模型和脱敏后的来源信息。

`faithfulness.json` 只能证明“转写结果 → 口播文案”没有增删非空白字符，不能证明语音识别本身 100% 正确。

## 无法访问 GitHub

发布时请同步提供 GitHub Release ZIP、SHA-256 校验值和 Gitee/其他可访问镜像。镜像只解决 Skill 下载，不能代替目标视频站点、Python 包索引或模型站点的网络可达性。

## 许可与安全

本项目使用 [MIT License](LICENSE)。安全和隐私问题请先阅读 [SECURITY.md](SECURITY.md)。
