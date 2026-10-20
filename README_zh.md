# Video Transcriber AI Skills

[Video Transcriber AI](https://videotranscriber.ai/) 官方 Skills：连接 AI 客户端，转写公开视频，并整理摘要、字幕和学习笔记。

[![Validate Skills](https://github.com/VideoTranscriberAI/videotranscriber-skills/actions/workflows/validate-skills.yml/badge.svg)](https://github.com/VideoTranscriberAI/videotranscriber-skills/actions/workflows/validate-skills.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[English](README.md) | [简体中文](README_zh.md)

## 第一次使用

1. 按下面对应客户端的说明安装。
2. 直接说：**“帮我连接 Video Transcriber。”** 接入 Skill 会引导填写凭证并检查连接。
3. 发一个公开音视频链接，说明需要全文、字幕、摘要还是学习笔记。

**转写使用独立的 API 额度，网站积分和无限会员权益不能抵扣。** 登录 [Video Transcriber AI](https://videotranscriber.ai/) 后，在 API 控制台创建 Key。在本地隐藏输入框或客户端凭证设置里粘贴一次，不要发到聊天中。已有文字、字幕的分析无需 API Key，也不消耗 Video Transcriber API 额度；宿主模型费用遵循客户端规则。

## 选择你使用的客户端

### ChatGPT Desktop with Codex / Codex CLI

在本机终端执行：

```bash
codex plugin marketplace add VideoTranscriberAI/videotranscriber-skills
codex plugin add videotranscriber-skills@video-transcriber-ai
```

添加 Marketplace 后，也可在桌面端 **Plugins Directory → Video Transcriber AI → Video Transcriber AI Skills** 中安装。打开新对话，告诉 AI“帮我连接 Video Transcriber”。

接入 Skill 会启动本地配置助手。你在隐藏输入框粘贴一次 Key，助手校验后保存连接配置，再引导刷新连接并继续原任务。Key 以明文保存在本机用户配置中，并限制文件权限；重启后无需再次填写。助手需要 Python 3.11+；无法打开本地窗口时会提供用户终端中的隐藏输入方式，详见[本地配置说明](skills/setup-videotranscriber/references/local-setup.md)。安装插件不会自动提供 Key。这里针对本地 Codex／插件接入路径；其他 ChatGPT 入口按其自身连接要求接入。

### Claude Code

在 Claude Code 对话中执行：

```text
/plugin marketplace add VideoTranscriberAI/videotranscriber-skills
/plugin install videotranscriber-skills@video-transcriber-ai
```

启用插件后，说“帮我连接 Video Transcriber”。有原生 **Video Transcriber API Key** 输入框时直接填写；没有时，接入 Skill 启动同一套[本地配置助手](skills/setup-videotranscriber/references/local-setup.md)，写入 Claude Code 用户配置并引导刷新连接。只分析已有文字时无需填写 Key。环境变量等高级方式见[客户端配置说明](skills/setup-videotranscriber/references/clients.md)。

### WorkBuddy

通过 **技能 → 添加技能 → 上传技能** 导入各 Skill 的 ZIP 包，然后说“帮我连接 Video Transcriber”。接入 Skill 会打开本地隐藏输入框，验证 Key 后保存 WorkBuddy 用户级 MCP 配置。详见 [WorkBuddy 安装与打包说明](docs/WORKBUDDY.md)。

仓库也提供带本地 Key 表单的 Token 连接器配置。进入连接器市场需要经过 WorkBuddy 审核；本仓库不代表连接器已上架。目标客户端的安装体验仍需实机验证。

### Cursor、Windsurf、Gemini CLI、Copilot、VS Code、Cline、Roo Code

按客户端支持的 Skill 安装方式安装本仓库的三个标准 Skill，也可以让 Agent 安装此仓库。支持 Skills CLI 的客户端可参考[高级安装说明](docs/INSTALLATION.md)。安装后直接描述视频任务，或说“帮我连接 Video Transcriber”。

接入 Skill 会按当前客户端启动同一套本地配置助手。你在隐藏输入框粘贴一次 Key，助手验证后保存该客户端的用户配置。遇到编辑器自定义 Profile，Agent 会先定位实际使用的用户 MCP 配置。客户端需要允许执行本地脚本；无法打开窗口时，使用原生凭证表单或用户终端隐藏输入。

各配置格式已覆盖自动化测试；Skill 识别、实际弹窗和连接刷新需要逐个客户端验收。查看[支持的客户端与配置位置](skills/setup-videotranscriber/references/local-setup.md)及[统一测试清单](docs/CLIENT_TESTING.md)。

## 直接用自然语言

```text
帮我连接 Video Transcriber，并检查连接状态。
```

```text
帮我转写这个视频，并整理成中文学习笔记：https://www.youtube.com/watch?v=e8WaTlzuid0
```

第二个示例使用官方产品视频，会创建真实转写任务并消耗 API 额度，不属于连接自检。

```text
继续查看刚才的转写。
```

```text
总结这份字幕，并提取待办事项。
```

无需记住 Skill 名称，也无需手动在转写、分析两个 Skill 之间传递文本。继续查询时会使用原任务，不重新创建。

## 没有 API Key 也能先体验

粘贴下面这段虚构字幕，告诉 AI“总结这份字幕”：

```srt
1
00:00:00,000 --> 00:00:04,000
今天我们比较了两种新手引导页面。

2
00:00:04,000 --> 00:00:09,000
我们选定更简洁的页面。小美将在周五前准备初稿。
```

这会直接分析已有字幕，不调用转写服务。仓库还提供[官方产品视频字幕](examples/transcript-insights/official-video-subtitles.srt)和[分析示例](examples/transcript-insights/official-video-expected-output.md)。

## 包含哪些 Skill

| Skill | 用途 |
| --- | --- |
| `setup-videotranscriber` | 引导连接、填写凭证、检查工具发现和恢复连接；自检不创建收费任务。 |
| `transcribe-media` | 转写公开链接、获取 SRT/VTT、继续查询任务，并把文本交给分析。 |
| `transcript-insights` | 根据要求生成摘要、洞察、待办、开放问题、翻译、章节、决策、学习笔记和思维导图。 |

未指定分析类型时，默认返回摘要、关键洞察、待办事项和开放问题。输出语言跟随用户，并保留原文依据。

## 支持范围

- 转写支持服务可处理的公开 HTTP/HTTPS 媒体链接和已有任务 ID。MCP 工具不负责上传本地或私有音视频。
- 文本分析支持直接粘贴内容，或客户端可读取的 TXT、Markdown、SRT、VTT、可识别的转录 JSON。
- 默认基础模型；高级模型、API 章节和翻译仅按需求启用。整理中文学习笔记不会自动开启额外收费的 API 功能。
- 失败任务不会自动重建；缺失的人名、负责人、日期、时间戳不会被猜测补齐。

## 连接帮助

服务地址为 `https://videotranscriber.ai/mcp`，使用 Bearer API Key 鉴权。查看[官方 MCP 接入说明](https://videotranscriber.ai/code-docs#mcp-overview)或[各客户端的连接步骤](skills/setup-videotranscriber/references/clients.md)。

安装 Skill 与验证连接是两个步骤，接入 Skill 会引导完成。只保存配置不代表连接已验证；自检不会创建转写任务，也不代表账户额度足够。

终端安装、手动复制和显式调用方式见[高级安装说明](docs/INSTALLATION.md)。开发资料：[架构](docs/ARCHITECTURE.md)、[贡献指南](CONTRIBUTING.md)、[路线图](ROADMAP.md)、[更新记录](RELEASE_NOTES.md)。

## 隐私与许可证

转写会将用户提供的媒体链接和所选参数发送到 Video Transcriber AI。字幕和文本分析在宿主 Agent 环境中完成，数据处理还受客户端配置及政策影响。不要提交私人字幕、凭证或签名下载链接。查看[产品隐私政策](https://videotranscriber.ai/privacy)。

本项目采用 [MIT License](LICENSE)。
