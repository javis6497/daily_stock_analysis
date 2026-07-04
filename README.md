# 股票/基金量化日报系统

这是一个 Python 量化日报系统 v1。它面向个人研究用途，支持自选股/基金分析、候选标的筛选、真实资讯聚合、盘前/盘后/周末 Markdown 报告，以及通过钉钉机器人推送。

系统只输出量化研究信号和风险提示，不接券商、不自动下单，不构成保证收益或个人投顾建议。

## 功能

- A 股、ETF、公募基金优先；港股/美股后续通过数据源适配器扩展。
- 稳健均衡策略：MA20/MA60、RSI、MACD、ATR、近期高低点和回撤控制。
- 输出自选标的状态：观察、偏强、偏弱、买入观察区、风险位、止盈/减仓观察位。
- 支持持仓成本、投入本金、目标仓位、最大仓位、风险等级、估算浮盈亏和基金名称自动补全。
- 操作建议会显示市场环境、持仓级建议、距离风险位、距离止盈/减仓观察位。
- 自选外候选池按趋势、风险、市场环境和行业/主题分散打分，推送 Top N 候选观察。
- 资讯摘要采用 AKShare 财经快讯源 + 规则过滤，不依赖 LLM。
- GitHub Actions 支持北京时间工作日 08:30 盘前、14:00 基金操作提醒、16:30 盘后，以及周六/周日 09:30 周末量化周报；每个定时任务带 +15 分钟、+30 分钟兜底触发。
- 工作日会拆成两条钉钉消息：操作建议一条，资讯摘要一条。
- GitHub Actions 运行失败时会尝试发送钉钉失败通知，附带 Actions 运行链接。

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
    target_weight: 0.20
    max_weight: 0.30
    risk_level: medium
    note: 核心基金
    tags: ["持仓", "基金"]
```

`holding_amount` 建议填写累计投入本金。`target_weight` 和 `max_weight` 是组合目标仓位和上限仓位，用小数表示，例如 `0.20` 表示 20%。若基金名称仍是 `基金018044` 这类占位名，AKShare 可用时会尝试自动补全基金简称。

自选外候选默认开启，会排除 `watchlist` 里的持仓。A 股候选会尝试使用 AKShare 实时 A 股列表，先按成交额、市值、涨跌幅、PE/PB 做基础过滤；ETF 候选会尝试使用 AKShare ETF 实时列表，按成交额和异常涨跌过滤。候选进入历史行情评分后，会限制同一行业/主题的数量，避免推送结果过度集中。

```yaml
recommendation:
  enabled: true
  include_default_universe: true
  include_dynamic_a_shares: true
  include_dynamic_etfs: true
  exclude_watchlist: true
  dynamic_a_share_limit: 20
  dynamic_etf_limit: 20
  min_turnover: 500000000
  min_etf_turnover: 100000000
  min_market_cap: 50000000000
  min_pe: 0
  max_pe: 80
  min_pb: 0
  max_pb: 10
  min_pct_change: -5
  max_pct_change: 7
  max_candidate_single_day_pct: 0.07
  max_candidates_per_group: 2
```

候选结果是“量化候选观察”，不是买入指令。

市场环境默认使用上证指数、沪深300、创业板指、中证500 的趋势和回撤来判断“进攻 / 中性 / 防守”，并在报告中给出仓位倾向。若指数数据源临时不可用，报告会降级提示，不影响自选标的信号生成。

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

周末报告是“周末量化周报”：包含市场环境、本周持仓回顾、本周涨跌、本周最大回撤、自选外候选更新、相关资讯、风险事件日历和下周观察计划。周末报告不生成具体交易价位或即时卖出指令。

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

- 操作建议：市场环境、自选标的信号、持仓成本/盈亏、持仓级建议、自选外候选观察。
- 资讯摘要：相关新闻和摘要。

工作日 `fund_action` 会在北京时间 14:00 单独发送一条基金操作提醒，只包含自选基金/ETF，不包含股票、资讯或自选外候选。

为降低 GitHub Actions 定时任务漏触发的影响，四类自动任务都会在原时间后追加两个兜底触发点，并用“北京时间日期 + session”的缓存标记跳过重复发送。手动触发 `workflow_dispatch` 不走去重限制，方便测试。

如果测试、数据获取或发送步骤失败，workflow 会尝试发送一条“量化日报任务失败”到钉钉，消息里包含本次 GitHub Actions 运行链接，便于直接定位失败步骤。

手动触发时可选择：

- `premarket`：盘前量化日报。
- `fund_action`：14:00 基金操作提醒。
- `postmarket`：盘后量化复盘。
- `weekend_news`：周末量化周报。
