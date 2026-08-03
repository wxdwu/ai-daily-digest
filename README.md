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

- 仓库的 `reports/latest.md`
- 仓库 **Issues** 中当天的“每日 AI 速报”
- 本次 Actions 运行页面底部的 artifact 压缩包

工作流每天也会自动运行。GitHub cron 使用 UTC，当前 `0 23 * * *` 对应次日北京时间 07:00，平台繁忙时可能延迟几分钟。

## 大模型怎么调用

默认使用 GitHub Actions 自动提供的 `GITHUB_TOKEN` 调用 GitHub Models，模型为 `openai/gpt-4.1-mini`。不需要手工创建 API Key，也不用在任何第三方网站登录。每份报告最多调用模型一次，用于从候选中选出 8–10 条精华、改写中文标题和摘要、总结三个趋势。

如果 GitHub Models 暂时不可用或触及单独的模型限额，任务不会失败，而是自动生成规则版中文报告。Actions 的运行分钟数与 GitHub Models 的调用额度是两套独立额度。

想换 GitHub Models 中的模型，可在 **Settings → Secrets and variables → Actions → Variables** 添加：

| Variable | 值 |
|---|---|
| `GITHUB_MODELS_MODEL` | 例如 `openai/gpt-4.1-mini` |

也可以改用兼容 OpenAI Chat Completions 的外部服务。在 **Settings → Secrets and variables → Actions → Secrets** 同时添加 `LLM_API_KEY`、`LLM_ENDPOINT` 和 `LLM_MODEL`；只配置其中一部分不会覆盖默认 GitHub Models。

## 邮件怎么配置（可选）

如果 GitHub Issue 已经够用，不需要配置邮件。要自动发送和抄送，请在 **Settings → Secrets and variables → Actions → Secrets** 添加：

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

这里唯一需要额外登录的是你的邮箱后台：开启 SMTP 服务并生成授权码。QQ、163 邮箱通常在邮箱设置中开启；Gmail 通常需要两步验证和 App Password。所有授权码都放 GitHub Secrets，不要写进代码。

## GitHub 权限检查

如果第一次运行在提交报告或创建 Issue 时提示权限不足，打开：

**Settings → Actions → General → Workflow permissions → Read and write permissions**

保存后重新运行。工作流已声明 `contents: write`、`issues: write` 和 `models: read`。

## 常用调整

- 来源、关键词和观察窗口：`config/sources.json`
- 关闭每日 Issue：添加 Repository variable `CREATE_DAILY_ISSUE=false`
- 忽略历史去重：手动运行时勾选 `ignore_seen`
- 修改自动运行时间：编辑 `.github/workflows/ai-daily.yml` 中的 cron

本地验证不需要第三方依赖：

```bash
python -m unittest discover -s tests -v
python -m src.ai_digest --ignore-seen
```

抓取、模型或单个来源失败都不会阻断整份日报，具体情况会写在报告的“运行状态”中。
