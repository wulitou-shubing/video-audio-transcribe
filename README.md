# video-audio-transcribe

一个本地优先的 Agent Skill：从视频链接或本地音视频生成带时间戳的逐字稿和口播文案。口播整理只能改变空白与分段，不允许增加、删除或调换转写字符。

当前版本：`v3.2.0`

[English](README.en.md)

## 功能

- 处理本地 MP4、MOV、MKV、MP3、M4A、WAV、SRT 和 VTT。
- 处理 yt-dlp 兼容的国内外网站，已针对 B 站、抖音、小红书、视频号设置清晰边界。
- 优先复用平台字幕；字幕可用时默认不再下载媒体，否则用 faster-whisper 本地转写。
- 可选下载完整视频或提取 MP3。
- 自动脱敏 URL 中常见的 token/签名参数，默认拦截本机和私网 URL。
- 默认不读取浏览器 Cookie，也不在非交互环境中静默安装依赖。
- WorkBuddy 默认不调用浏览器控制、Cookie、逐帧 OCR、截图识别或其他 skill；公开 URL 失败后只要求用户提供本地媒体文件。
- WorkBuddy/Windows 前台进程可持续跟踪，下载和完整结果默认断点复用。
- 兼容 Codex、通用 Agent Skills 目录和 WorkBuddy。

## 快速开始

需要 Python 3.9 或更高版本。

从 GitHub/Gitee 克隆仓库，或下载 Release ZIP 并解压。进入 `video-audio-transcribe` 目录后运行：

```bash
python scripts/install_skill.py --host workbuddy
```

如果不确定宿主，可使用 `--host auto`。它只会选择一个最合适的位置，优先 WorkBuddy，其次 Codex，再其次通用 Agent Skills。安装器会原地更新受管文件，不删除整个 Skill 目录；`--host all` 仅给维护者手动同步多个宿主使用。

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

默认不读取 Cookie，也不控制浏览器。公开访问失败后，在 WorkBuddy/新手模式中直接让用户从自己已登录、已授权的浏览器里保存/导出视频或音频文件，再把本地文件交给 Skill。

高级 CLI 用户如果明确要求 Cookie 文件，可使用只包含目标站点的 Netscape Cookie 文件：

```bash
python scripts/run.py URL --cookie-file /path/to/cookies.txt
```

运行器会拒绝混入其他站点 Cookie 的文件，不会复制、保存或清理临时 Cookie 副本。`--cookies chrome` 等直接浏览器读取仅保留为专家级、单浏览器、明确授权兜底；WorkBuddy 默认流程不要使用它。

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
