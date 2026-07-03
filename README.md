# 股票/基金量化日报系统

这是一个 Python 量化日报系统 v1。它面向个人研究用途，支持自选股/基金分析、候选标的筛选、真实资讯聚合、盘前/盘后/周末 Markdown 报告，以及通过钉钉机器人推送。

系统只输出量化研究信号和风险提示，不接券商、不自动下单，不构成保证收益或个人投顾建议。

## 功能

- A 股、ETF、公募基金优先；港股/美股后续通过数据源适配器扩展。
- 稳健均衡策略：MA20/MA60、RSI、MACD、ATR、近期高低点和回撤控制。
- 输出自选标的状态：观察、偏强、偏弱、买入观察区、风险位、止盈/减仓观察位。
- 支持持仓成本、投入本金、估算浮盈亏和基金名称自动补全。
- 自选外候选池按趋势、风险和资产类型打分，推送 Top N 候选观察。
- 资讯摘要采用 AKShare 财经快讯源 + 规则过滤，不依赖 LLM。
- GitHub Actions 支持北京时间工作日 08:30 盘前、14:00 基金操作提醒、16:30 盘后，以及周六/周日 09:30 周末资讯观察。
- 工作日会拆成两条钉钉消息：操作建议一条，资讯摘要一条。

## 本地运行

```powershell
python -m pip install -r requirements.txt
Copy-Item config/watchlist.example.yml config/watchlist.yml
python -m stock_quant report --session premarket --config config/watchlist.yml --dry-run
python -m stock_quant report --session fund_action --config config/watchlist.yml --dry-run
python -m stock_quant report --session postmarket --config config/watchlist.yml --dry-run
python -m stock_quant report --session weekend_news --config config/watchlist.yml --dry-run
python -m stock_quant backtest --config config/watchlist.yml --sample-data
```

`config/watchlist.yml` 已被 `.gitignore` 忽略。真实自选股、基金和偏好不要提交到 GitHub。

## 配置真实数据

示例配置默认使用 `sample` 数据源，便于先验证流程。要使用 AKShare，把 `config/watchlist.yml` 中的数据源改为：

```yaml
data:
  provider: akshare
  lookback_days: 180
```

如未安装 AKShare，真实数据模式会提示安装依赖；测试不会访问网络。

持仓成本和投入本金只写在你的 `WATCHLIST_YAML` Secret 里：

```yaml
watchlist:
  - symbol: "018044"
    name: 基金018044
    market: cn
    asset_type: fund
    cost_price: 2.0000
    holding_amount: 10000
    tags: ["持仓", "基金"]
```

`holding_amount` 建议填写累计投入本金。若基金名称仍是 `基金018044` 这类占位名，AKShare 可用时会尝试自动补全基金简称。

自选外候选默认开启，会排除 `watchlist` 里的持仓：

```yaml
recommendation:
  enabled: true
  include_default_universe: true
  exclude_watchlist: true
```

候选结果是“量化候选观察”，不是买入指令。

资讯源默认使用 AKShare：

```yaml
news:
  provider: akshare
  keywords:
    - 政策
    - 基金
    - ETF
  max_items: 8
```

周末报告只推送资讯和下周关注点，不生成买卖区间或交易动作。

## 钉钉推送

本地发送前设置环境变量：

```powershell
$env:DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=..."
$env:DINGTALK_SECRET="SEC..."
python -m stock_quant report --session premarket --config config/watchlist.yml --send
```

## GitHub Actions

建议使用私有仓库。仓库 Secrets：

- `DINGTALK_WEBHOOK`：钉钉机器人 webhook。
- `DINGTALK_SECRET`：钉钉加签密钥，可为空但不建议。
- `WATCHLIST_YAML`：完整的 `config/watchlist.yml` 内容。若不设置，workflow 会用示例配置。

上传后可以在 Actions 页面手动触发 `Daily Quant Report`，确认钉钉收到测试报告。

工作日 `premarket` / `postmarket` 会发送两条钉钉消息：

- 操作建议：自选标的信号、持仓成本/盈亏、自选外候选观察。
- 资讯摘要：相关新闻和摘要。

工作日 `fund_action` 会在北京时间 14:00 单独发送一条基金操作提醒，只包含自选基金/ETF，不包含股票、资讯或自选外候选。

手动触发时可选择：

- `premarket`：盘前量化日报。
- `fund_action`：14:00 基金操作提醒。
- `postmarket`：盘后量化复盘。
- `weekend_news`：周末资讯观察。
