# 每日 AI 速报

每天北京时间 07:00 自动生成一份精简中文 AI 报告，重点覆盖：

- 大模型：新模型、能力、训练、后训练与评测
- AI Infra：芯片、算力、训练与推理系统、Serving、量化和性能优化
- AI Agent：智能体、工具调用、MCP、Coding Agent 和工作流
- AI 最新动态：产业发布、融资收购、政策、安全与行业变化

系统先读取国际一手来源作为“事件雷达”，再到中文来源中寻找对应报道。只有标题、正文和链接均通过中文页面校验的条目才会进入报告，因此成品不会直接放英文原文链接。当前中文来源包括量子位、InfoQ 中文、NVIDIA 中文博客、NVIDIA 开发者中文博客和 AWS 中文博客。

## 现在怎么测试

代码进入 `main` 后，只需要：

1. 打开仓库的 **Actions**。
2. 左侧选择 **每日 AI 速报**。
3. 点击右上角 **Run workflow**。
4. 分支保持 `main`，第一次测试建议勾选 `ignore_seen`，再点绿色按钮运行。

运行完成后可以在三个地方看结果：

- 配置的收件邮箱
- 仓库的 `reports/latest.md`
- 本次 Actions 运行页面底部的 artifact 压缩包

Markdown 和邮件使用同一份精简内容：一句“今日 AI 猛料”总概括，加上最多 10 条资讯。每条包含可直接点击的精炼中文标题、分类、发布时间和一段短介绍；不显示媒体出处和“为什么值得看”。邮件同时提供 HTML 与纯文本正文，在支持 HTML 的邮箱中标题可以直接点击。

工作流每天也会自动运行。GitHub cron 使用 UTC，当前 `0 23 * * *` 对应次日北京时间 07:00，平台繁忙时可能延迟几分钟。

## 大模型怎么调用

不配置模型也能直接运行：系统会用确定性规则挑选并生成全中文报告。配置模型后，每份报告最多调用一次，用于从候选中选出最多 10 条精华、改写一句总概括和精炼标题。

GitHub Actions 的免费运行分钟只提供服务器，不自带大模型额度。并且 [GitHub Models 已于 2026-07-30 全面下线](https://docs.github.com/en/github-models)，所以这里不再使用已经失效的 `GITHUB_TOKEN + models: read` 方案。

要启用大模型精编，需要登录你选择的模型服务商，创建一个兼容 OpenAI Chat Completions 的 API Key，然后在 **Settings → Secrets and variables → Actions → Secrets** 同时添加：

| Secret | 说明 |
|---|---|
| `LLM_API_KEY` | 模型服务 API Key |
| `LLM_ENDPOINT` | 完整的 Chat Completions 接口地址 |
| `LLM_MODEL` | 该账号可用的模型名称 |

三项必须同时填写；未配置完整时自动使用规则版，不会导致 Actions 失败。模型只会收到候选的中文标题、短摘要、来源、分类和时间，不会收到链接或任何 GitHub 密钥。

## 每天会不会消耗 Token

RSS 抓取、中文网页校验、报告生成、仓库存档和 SMTP 邮件都不消耗大模型 Token，它们只占用 GitHub Actions 运行分钟。

只有同时配置 `LLM_API_KEY`、`LLM_ENDPOINT`、`LLM_MODEL` 时，每份报告才会调用一次外部模型，并按该模型服务商的输入、输出 Token 规则计费。没有配置完整这三项时使用本地规则版，因此大模型 Token 消耗为 0。

## 邮件怎么配置（必需）

GitHub Issue 已停用，邮件是唯一通知渠道。请在 **Settings → Secrets and variables → Actions → Secrets** 添加：

| Secret | 说明 |
|---|---|
| `SMTP_HOST` | SMTP 服务器，例如 QQ 邮箱 `smtp.qq.com` |
| `SMTP_PORT` | SSL 常用 `465`；STARTTLS 常用 `587` |
| `SMTP_USERNAME` | SMTP 用户名，通常是完整邮箱地址 |
| `SMTP_PASSWORD` | 邮箱生成的 SMTP 授权码，不是网页登录密码 |
| `SMTP_STARTTLS` | 587 端口填 `true`；465 填 `false` 或不填 |
| `EMAIL_FROM` | 发件人邮箱 |
| `EMAIL_TO` | 收件人，多个地址用逗号分隔 |
| `EMAIL_CC` | 可选抄送，多个地址用逗号分隔 |

这里需要额外登录你的邮箱后台：开启 SMTP 服务并生成授权码。QQ、163 邮箱通常在邮箱设置中开启；Gmail 通常需要两步验证和 App Password。所有授权码都放 GitHub Secrets，不要写进代码。缺少必需配置时，`Send email` 步骤会明确列出缺失的 Secret 名称并失败，不会静默跳过。

## GitHub 权限检查

如果第一次运行在提交报告时提示权限不足，打开：

**Settings → Actions → General → Workflow permissions → Read and write permissions**

保存后重新运行。工作流只声明报告归档所需的 `contents: write`。

## 常用调整

- 来源、关键词和观察窗口：`config/sources.json`
- 忽略历史去重：手动运行时勾选 `ignore_seen`
- 修改自动运行时间：编辑 `.github/workflows/ai-daily.yml` 中的 cron

本地验证不需要第三方依赖：

```bash
python -m unittest discover -s tests -v
python -m src.ai_digest --ignore-seen
```

抓取、模型或单个来源失败都不会阻断整份日报，具体情况保留在 Actions 运行日志中，不会混入极简报告正文。
