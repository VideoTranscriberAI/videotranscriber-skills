# ClawHub 发布与验收

本仓库向 ClawHub 提供 Codex 格式的 bundle 插件，包含三个标准 Skill 和远程 MCP 连接。用户使用自己的 API Key；服务地址为 `https://videotranscriber.ai/mcp`。此文档描述发布流程，执行构建不会提交 Git、推送代码或发布远端版本。

## 构建输入与产物

`integrations/clawhub/plugin.json` 只覆盖展示信息；名称、版本、作者、仓库地址和 MIT 许可证来自现有 Codex 清单。`integrations/clawhub/mcp.json` 声明 Streamable HTTP 和字面占位符 `Bearer ${VS_API_KEY}`。用户接入必须同时完成 Gateway 的 `VS_API_KEY` 环境绑定和原生 `mcp.servers.videotranscriber` 配置，由 Gateway 配置加载器展开请求头引用。原生配置使用相同服务名覆盖包内连接；仅安装包并设置环境变量不足以完成鉴权配置。

```bash
python3 scripts/validate_repository.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/build_clawhub_bundle.py --check
python3 scripts/build_clawhub_bundle.py
```

仓库校验需要 CI 已使用的 PyYAML 6.0.2；构建脚本只使用 Python 3.11+ 标准库。默认输出为 `dist/clawhub/videotranscriber-skills/`，已有目录会被拒绝覆盖。重新构建时选择一个新输出路径：

```bash
python3 scripts/build_clawhub_bundle.py --output /absolute/new/review-bundle
```

产物包含唯一的 `.codex-plugin/plugin.json`、`.mcp.json`、三个 Skill、图标、README 和 MIT LICENSE。显式文件白名单排除其他客户端清单、源码仓库管理文件、环境文件和运行数据；符号链接输入、缺失文件及引用未打包文件的 Markdown 会使构建失败。构建不读取或展开当前环境的 Key。

OpenClaw 元数据只写入产物中的 Skill 副本，不改源码 frontmatter。setup/transcribe 声明可选 `VS_API_KEY` 环境变量；纯文本分析不声明 Key 依赖，也不设置会阻止无 Key 用户加载接入说明的必需环境门槛。

## ClawHub 本地预检

使用已核实版本的 `clawhub` CLI。先检查帮助和实际支持的参数，记录 CLI 版本，再执行无上传预检：

```bash
clawhub --cli-version
clawhub package publish ./dist/clawhub/videotranscriber-skills --family bundle-plugin --bundle-format codex --name videotranscriber-skills --display-name "Video Transcriber AI Skills" --version 0.4.2 --dry-run
```

ClawHub CLI 0.26.0 的 bundle 发布不会从插件清单自动取得版本号；必须显式传入 `--version`，并与产物清单一致。示例的 `0.4.2` 是当前源码版本。显式 `--name` 避免自定义输出目录名变成注册表包名；正式注册表名称须与实际发布者和可用名称匹配。

预检必须识别为 `bundle-plugin` / `codex`，并核对名称、版本、发布者、源仓库、源 commit 和实际上传文件。仓库根目录有两种客户端清单，不能作为发布输入。未提交的本地改动不属于 HEAD；本地预检不能证明最终源码溯源已完成。若显式填写源码信息，`--source-repo` 与 `--source-commit` 必须成对提供；不要把基线 commit 声明成尚未提交改动的完整来源。正式发布应从获准提交的源码 commit 重建，并确认上传字节与审阅产物一致。

发布者 handle、包名与版本可用性需要在 ClawHub 账号下核实。GitHub 组织成员身份不自动证明 ClawHub 发布权限。不要把普通发布流程替换为仅平台管理员可用的 `clawhub-admin managed-mcp`。

CLI 预检不证明运行成功，也不替代 ClawHub 上传后的自动安全检查。预检要求登录时，由维护者完成账号授权，不打印 token。

## OpenClaw 实机验收

在隔离的测试用户或命名 Profile 中安装审阅过的 bundle，记录 OpenClaw 版本和产物摘要。仅检查默认路径不代表已验证所有部署方式。

```bash
openclaw plugins install /absolute/review-bundle
openclaw plugins inspect videotranscriber-skills
```

按产物内的 [OpenClaw 接入说明](../skills/setup-videotranscriber/references/openclaw.md)配置实际 Gateway/profile 的环境变量和必需的原生 MCP 连接，保留其他连接及已有有效凭证。检查以下场景：

| 场景 | 验收结果 |
| --- | --- |
| 无 Key | 接入说明和已有文字/SRT 分析可用；转写连接明确不可用，不循环索取凭证 |
| 原生连接绑定 | 使用非敏感占位测试值检查 Gateway 配置加载后的请求头已展开；只记录判断结果，不输出值。确认同名原生连接覆盖包内连接，单独安装包或设置环境变量不计为通过 |
| 正确 Key | 必需的环境变量和原生连接均已应用；认证握手成功，当前会话发现三个工具；不通过创建任务检查连接 |
| 重启 Gateway | 使用同一用户/Profile 的原生连接与凭证，重启后重新发现工具；前台进程继承环境与后台服务持久化环境分别记录，前台通过不代替后台服务验收 |
| 错误或撤销的 Key | 给出明确凭证错误，日志无 Key，无自动付费重试 |
| 网关 401/403、网络超时 | 与 API 凭证错误区分，连接检查有上限 |
| 真实转写 | 事先明确测试账号、输入和额度范围；创建、轮询、结果完整闭环 |
| 已有任务复验 | 复用记录中的 `request_id`，只调用 `get_transcription` 和 `get_transcription_result`，核对正文与字幕存在性；结果过期或不可用时记录原因，不新建替代任务 |
| 创建响应丢失、限流、额度不足 | 保留原幂等键和参数；退避或停止，不重复创建 |
| processing 超出等待预算 | 保留原任务 ID，可继续查询；不把客户端等待上限当后端失败 |
| 结果过期、失败或取消 | 报告实际终态，不自动创建替代任务 |
| 远程 Gateway/多 Profile | Key 和连接只配置到实际服务实例，保留其他连接 |

未执行的场景记录为“未验证”，不能以打包测试通过代替实机验收。若缺少有效 Key 或目标 OpenClaw 环境，交付本地包和已经完成的验证结果，并列明剩余场景。

## 正式发布与更新

正式发布必须有明确授权。核实发布者和唯一版本、源码 commit、包内文件、安装验收及安全扫描要求后，去掉 `--dry-run` 并使用 CLI 支持的等待发布结果参数。上传成功与公开可安装分开记录；安全检查未通过时不能宣称已上架。

更新时使用新的已审阅源码版本和不可变版本号，先本地预检及安装验收，再发布。版本已经存在时停止，不擅自删除、覆盖或递增其他客户端版本。发布不会自动更新用户已经安装的插件；维护者需提供正常更新说明。

此包使用仓库现有 MIT 许可证。本流程不另外创建 Skills 栏目的独立 Skill 条目；独立条目需按该栏目 MIT-0 规则另行确认。

## 配置与运维范围

用户侧配置项只有实际 Gateway 使用的 `VS_API_KEY` 及 MCP 连接。构建和文档不包含真实值。VS 后端、数据库 DDL、线上配置和 OAuth 不在本流程修改范围内。

官方契约：[bundle 格式](https://docs.openclaw.ai/plugins/bundles)、[ClawHub CLI](https://docs.openclaw.ai/clawhub/cli)、[Skill 元数据](https://docs.openclaw.ai/clawhub/skill-format)。
