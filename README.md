# AI Daily Digest

每天 07:00（Asia/Shanghai）自动抓取、去重并筛选 AI 最新资讯，重点覆盖：

- 大模型：新模型、能力、评测、训练与后训练
- AI Infra：训练/推理系统、GPU、Serving、量化、性能优化
- AI Agent：Agent 框架、工具调用、MCP、Coding Agent、工作流

默认读取公开 RSS、Anthropic sitemap、arXiv 分类 RSS、Hacker News 和核心开源项目的 GitHub Releases。单个来源失败不会拖垮整次任务。产物包括每日 Markdown、机器可读 JSON、GitHub Actions artifact，以及默认开启的每日 GitHub Issue。

## 1. 放到 GitHub

新建一个 GitHub 仓库（公开或私有都可以），把本目录内容推上去。然后：

1. 打开仓库的 **Actions** 页，允许工作流运行。
2. 在 **Actions → AI Daily Digest → Run workflow** 手动跑一次。
3. 确认 `reports/latest.md`、当天归档和当天 Issue 正常生成。

定时表达式在 `.github/workflows/ai-daily.yml`，当前是每天北京时间 07:00。想改成 09:00，把 cron 从 `0 23 * * *` 改为 `0 1 * * *`。GitHub 的定时任务偶尔会因平台负载延迟几分钟。

如果组织策略不允许工作流写仓库，需要到 **Settings → Actions → General → Workflow permissions** 选择 **Read and write permissions**。工作流本身已声明 `contents: write` 和 `issues: write`。

## 2. 哪些地方需要登录或密钥

### 核心抓取：不需要额外登录

所有资讯源均是公开接口或公开网页。只需要你的 GitHub 账号和仓库；Actions 自动提供 `GITHUB_TOKEN`，不用手工创建 Personal Access Token。

### 中文摘要与“为什么值得看”：可选

不配置时，简报仍会正常生成，但会保留英文标题和来源摘要。若要自动翻译和编辑成中文，需要一个支持 OpenAI Chat Completions 兼容协议的模型服务账号，并在：

**Settings → Secrets and variables → Actions → Secrets**

添加：

| Secret | 示例/说明 |
|---|---|
| `LLM_API_KEY` | 模型服务 API Key |
| `LLM_ENDPOINT` | 完整接口地址，例如 `https://你的服务/v1/chat/completions` |
| `LLM_MODEL` | 该账号可用的模型名称 |

三项必须一起配置。脚本只把入选条目的标题和短摘录发给模型，不会发送 GitHub 密钥。模型失败时自动降级成无润色版本。

### 邮件和抄送：可选

若每天 Issue 已经够用，完全不需要邮件账号。想把简报发到邮箱，再添加：

| Secret | 说明 |
|---|---|
| `SMTP_HOST` | SMTP 服务器，例如 Gmail 为 `smtp.gmail.com` |
| `SMTP_PORT` | SSL 通常 `465`；STARTTLS 通常 `587` |
| `SMTP_USERNAME` | SMTP 登录用户名 |
| `SMTP_PASSWORD` | Gmail App Password / QQ 邮箱授权码；不要填日常登录密码 |
| `SMTP_STARTTLS` | 587 端口填 `true`；465 可不填或填 `false` |
| `EMAIL_FROM` | 发件人地址 |
| `EMAIL_TO` | 收件人；多人用逗号分隔 |
| `EMAIL_CC` | 可选抄送；多人用逗号分隔 |

Gmail 需要登录 Google 账号、开启两步验证并创建 App Password；QQ/163 等邮箱通常要在邮箱设置里开启 SMTP 并生成授权码。所有值都放 GitHub Actions Secrets，不要写进源码。

## 3. 常用配置

- 资讯源与权重：`config/sources.json` 的 `sources`
- 三类关键词与分数：`config/sources.json` 的 `categories`
- 每期数量：`max_items` 和 `per_category`
- 观察窗口：默认 36 小时，手动运行时可临时修改
- 关闭每日 Issue：添加 Repository variable `CREATE_DAILY_ISSUE=false`
- 已读去重：`data/seen.json` 保留 30 天；手动运行可勾选 `ignore_seen`

排序综合考虑关键词相关度、来源权重、发布时间和 HN 热度。不是简单把所有 AI 新闻堆在一起。

## 4. 本地运行与测试

要求 Python 3.11+，没有第三方依赖：

```bash
python -m unittest discover -s tests -v
python src/ai_digest.py --ignore-seen
```

本地如需启用模型或邮件，用环境变量注入密钥；不要创建会被提交的密钥文件。

## 5. 维护建议

RSS 地址会变化，但失败源只会显示在报告的“运行状态”中。每隔一段时间看一次该区块：连续失败的源可以在 `config/sources.json` 替换或删除。GitHub Releases、arXiv 和 HN 通常比网页选择器稳定。
