# 外部准点调度器

GitHub 官方不保证 `schedule` 准点执行，高负载时任务可能延迟或被丢弃。本目录提供一个独立的 Cloudflare Worker 时钟。Worker 在每个发送窗口前触发两次 GitHub `daily-report.yml`，GitHub 端用持久发送回执去重。

## 调度时间

| 报告 | 北京时间目标 | Worker 触发 |
| --- | --- | --- |
| 盘前 | 工作日 08:37 | 08:27、08:32 |
| 基金操作 | 工作日 14:07 | 13:57、14:02 |
| 盘后 | 工作日 16:37 | 16:27、16:32 |
| 周末 | 周六、周日 09:37 | 09:27、09:32 |

Worker 使用 UTC cron，配置已写在 `wrangler.toml`。

## 一次性部署（全程网页，推荐）

1. 在 GitHub 创建 fine-grained personal access token，只授权 `javis6497/daily_stock_analysis`，Repository permissions 中将 `Actions` 设为 `Read and write`。
2. 在 Cloudflare `Workers & Pages` 中创建 Worker，选择连接 GitHub 仓库 `javis6497/daily_stock_analysis`。
3. 生产分支选 `main`，Root directory 填 `scheduler`，Deploy command 使用 `npx wrangler deploy`。
4. 部署后进入 Worker 的 `Settings -> Variables & Secrets`，添加以下运行时 Secrets：
   - `GITHUB_TOKEN`：第 1 步的 token。
   - `SCHEDULER_ADMIN_TOKEN`：自行生成的长随机字符串，只用于手动触发接口。
   - `DINGTALK_WEBHOOK`：现有钉钉 webhook，用于外部调度彻底失败时报警。
   - `DINGTALK_SECRET`：现有钉钉加签密钥。
5. 打开 Worker 地址的 `/health`，应返回：

```json
{"ok":true,"scheduler":"stock-quant-scheduler"}
```

6. GitHub 仓库必须允许 Actions 执行。四个旧的定时 wrapper 可以保持关闭；Worker 每次会先启用核心 `Daily Quant Report`，再调用 `workflow_dispatch`。

也可以用 Wrangler CLI 部署：

```powershell
npm install
npx wrangler login
npx wrangler secret put GITHUB_TOKEN
npx wrangler secret put SCHEDULER_ADMIN_TOKEN
npx wrangler secret put DINGTALK_WEBHOOK
npx wrangler secret put DINGTALK_SECRET
npx wrangler deploy
```

## 手动验证

目标时间必须处于当前北京时间前后 5 分钟，否则核心任务会拒绝发送。

```powershell
$headers = @{ Authorization = "Bearer 你的SCHEDULER_ADMIN_TOKEN" }
Invoke-RestMethod -Method Post `
  -Uri "https://你的Worker地址/trigger?session=premarket&target=当前HH:mm" `
  -Headers $headers
```

Worker 对 GitHub API 失败最多重试 3 次；每个时间段还有两次独立触发。GitHub 端会记录每条消息的每个分片，后续重跑只补发未成功的部分。三次 API 重试全部失败时，Worker 直接向钉钉发送调度器故障提示，不依赖 GitHub 邮件。

## 邮件通知

定时任务传入 `silent_failure=true`，内部失败不会把定时 workflow 标记为红色，因此不会产生“失败 workflow”邮件。CI 仍会严格失败，避免错误代码悄悄进入 `main`。

要彻底关闭所有 GitHub Actions 邮件，还需在 GitHub 个人 `Settings -> Notifications -> System -> Actions` 选择 `Don't notify`。这属于个人账号设置，仓库代码无法代改。
