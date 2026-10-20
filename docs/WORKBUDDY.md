# WorkBuddy 接入与打包

本仓库提供三个标准 Skill 和一个使用 API Key 的 MCP 连接器适配层。服务端继续使用现有 API Key 与 API Quota，无需 OAuth。

## 用户安装

1. 获取由本仓库源码打包的 `setup-videotranscriber.zip`、`transcribe-media.zip`、`transcript-insights.zip`。打包命令见下文；这里不声明存在已发布的下载附件。
2. 在 WorkBuddy 的 **技能 → 添加技能 → 上传技能** 中逐个导入。Skill 包与连接器提交包用途不同，不能把连接器 ZIP 当成单个 Skill 上传。
3. 在对话中说“帮我连接 Video Transcriber”。接入 Skill 启动共享的本地配置助手（`--client workbuddy`），打开隐藏输入框；用户粘贴一次 Key，助手完成握手验证后保存 `~/.workbuddy/mcp.json`。无法执行本地脚本时，按引导在客户端原生自定义 MCP 表单中填写服务 URL 与 Bearer Key。
4. 保存并刷新连接，检查三个工具是否可用。连接检查不提交转写任务；验证成功后再发送媒体链接。

若已经安装通过平台审核的 Token 连接器，在连接器的密码输入框粘贴 API Key 即可，由表单注入请求头。不要假设当前市场中已经存在该条目。当前仓库包含适配配置和打包测试，目标 WorkBuddy 版本的安装、凭证保存和工具发现仍需实机验收。

安装行为依据 [WorkBuddy 技能上传说明](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)。界面名称可能随版本调整。

## 为用户生成 Skill 上传包

在仓库根目录运行，脚本需要 Python 3.10 或更新版本，只使用标准库：

```bash
python3 scripts/build_workbuddy_connector.py --skill setup-videotranscriber
python3 scripts/build_workbuddy_connector.py --skill transcribe-media
python3 scripts/build_workbuddy_connector.py --skill transcript-insights
```

输出位于 `dist/`。每个 Skill ZIP 根目录都包含 `SKILL.md` 及该 Skill 的引用和资源。默认不覆盖已有包；更新时通过 `--output` 选择新文件名。三个包都从 `skills/` 中读取，不维护平台专属副本。发布附件需按项目发布流程单独执行。

## 为平台审核生成连接器包

```bash
python3 scripts/build_workbuddy_connector.py
```

默认生成 `dist/videotranscriber-workbuddy.zip`，包含：

```text
connector-meta.json
mcp.json
token-schema.json
icon.png
skills/
  setup-videotranscriber/
  transcribe-media/
  transcript-insights/
```

适配配置位于 `integrations/workbuddy/`。`auth_mode: token` 声明本地凭证表单，`VS_API_KEY` 对应 `Authorization` 中的占位变量。包含双语示例，因此最低版本为 WorkBuddy 4.24.0。源码和 ZIP 中都不包含真实 Key。

按照 [WorkBuddy 连接器规范](https://open.workbuddy.cn/docs/connector)提交平台审核；本次代码修改不提交审核或上架。平台审核通过并完成实机验收后，才能向用户提供对应市场安装入口。

## 验证

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

覆盖归档内的共享 Skill 内容、入口与引用、凭证表单和请求头变量匹配、现有输出文件保护。实机还需检查安装、Key 输入与更新、重启后连接、无 Key 的文本分析，以及网络或鉴权失败时的恢复步骤。
