# video-audio-transcribe

一个本地优先的 Agent Skill：从视频链接或本地音视频生成带时间戳的逐字稿和口播文案。口播整理只能改变空白与分段，不允许增加、删除或调换转写字符。

当前版本：`v3.1.1`

[English](README.en.md)

## 功能

- 处理本地 MP4、MOV、MKV、MP3、M4A、WAV、SRT 和 VTT。
- 处理 yt-dlp 兼容的国内外网站，已针对 B 站、抖音和小红书设置清晰的失败与 Cookie 回退路径。
- 优先复用平台字幕，否则用 faster-whisper 本地转写。
- 可选下载完整视频或提取 MP3。
- 自动脱敏 URL 中常见的 token/签名参数，默认拦截本机和私网 URL。
- 默认不读取浏览器 Cookie，也不在非交互环境中静默安装依赖。
- 登录内容优先通过已授权浏览器把媒体交付到本地，不暴露 Cookie 值；Cookie 文件会按目标站点过滤。
- WorkBuddy/Windows 前台进程可持续跟踪，下载和完整结果默认断点复用。
- 兼容 Codex、通用 Agent Skills 目录和 WorkBuddy。

## 快速开始

需要 Python 3.9 或更高版本。

从 GitHub/Gitee 克隆仓库，或下载 Release ZIP 并解压。进入 `video-audio-transcribe` 目录后运行：

```bash
python scripts/install_skill.py --host auto
```

`--host auto` 会检测已存在的 Agent Skills/Codex/WorkBuddy 目录；也可显式使用 `agents`、`codex`、`workbuddy` 或 `all`。安装器不会覆盖已存在的 Skill，除非传入 `--force`。

首次使用只进行一次合并确认，准备隔离运行时和 Whisper 模型：

```bash
python scripts/setup.py
```

在 WorkBuddy 等非交互宿主中，Agent 应先向用户展示完整安装计划并只确认一次，然后运行 `python scripts/setup.py --yes`。安装过程不会读取浏览器 Cookie。

也可不安装，直接在仓库中运行：

```bash
python scripts/run.py "视频链接或本地文件" --output-dir transcription-output
```

任务被宿主中断时，使用相同命令和相同输出目录重跑；已验证结果、模型缓存和媒体分片会自动复用。

## Cookie 与登录

默认不读取 Cookie。公开访问失败后，优先让用户授权 WorkBuddy/Codex 的现有浏览器会话打开目标页并把视频保存为本地文件，再将本地文件交给 Skill；这个过程不提取 Cookie 值。

浏览器交付不可用时，使用只包含目标站点的 Netscape Cookie 文件：

```bash
python scripts/run.py URL --cookie-file /path/to/cookies.txt
```

运行器只会复制与目标平台匹配的 Cookie 到权限受限的临时文件，排除其他站点 Cookie，并在本次尝试后删除临时副本。`--cookies chrome` 等直接浏览器读取仅保留为明确授权的单浏览器高级兜底；不会自动检测或轮询浏览器。

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

完全离线机器仍使用同一个版本：准备兼容系统的 wheels 和本地 CTranslate2 模型后运行：

```bash
python scripts/setup.py --offline --wheel-dir WHEELS --model-path MODEL_DIR
```

## 许可与安全

本项目使用 [MIT License](LICENSE)。安全和隐私问题请先阅读 [SECURITY.md](SECURITY.md)。
