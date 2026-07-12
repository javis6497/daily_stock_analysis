# 股票/基金量化日报系统

这是一个 Python 量化日报系统 v1。它面向个人研究用途，支持自选股/基金分析、候选标的筛选、真实资讯聚合、盘前/盘后/周末 Markdown 报告，以及通过钉钉机器人推送。

系统只输出量化研究信号和风险提示，不接券商、不自动下单，不构成保证收益或个人投顾建议。

## 功能

- A 股、ETF、公募基金优先；港股/美股后续通过数据源适配器扩展。
- 稳健均衡策略：MA20/MA60、RSI、MACD、ATR、近期高低点和回撤控制。
- 输出自选标的状态：观察、偏强、偏弱、买入观察区、风险位、止盈/减仓观察位。
- 支持持仓成本、投入本金、目标仓位、最大仓位、风险等级、估算浮盈亏和基金名称自动补全。
- 操作建议会显示市场环境、持仓级建议、距离风险位、距离止盈/减仓观察位。
- 操作建议会生成组合总览、数据新鲜度检查和策略回测摘要。
- 自选外候选池按趋势、风险、市场环境、基金质量画像、A 股基本面质量画像和行业/主题分散打分，推送 Top N 候选观察。
- 14:00 基金操作提醒支持代理 ETF/指数的盘中估算，辅助 15:00 前人工决策。
- 支持持仓逻辑跟踪：在配置里写入持有理由、主要风险和失效条件后，日报会提示“有效 / 观察 / 逻辑漂移”。
- 支持日报质检：发送前用规则检查过强交易指令、收益承诺、缺少风险提示或免责声明，结果写入报告和台账。
- 报告会输出目标仓位建议区间，并在仓位超限、跌破风险位、数据滞后时单独发送异常提醒。
- 每次运行可生成结构化 JSON/CSV 信号台账和静态 HTML 看板；看板中的每只持仓可独立折叠，展开后显示最近 90 根 K 线、MA20/MA60、成本线、风险位和止盈位。
- 钉钉持仓正文使用紧凑摘要；GitHub Pages 开启后，持仓名称可点击并直接展开网页中的对应图表。
- 交易日判断使用上交所交易日历，不再把法定休市日简单当作普通工作日；AKShare 行情请求支持重试和最近有效缓存降级。
- 资讯摘要采用 AKShare 财经快讯源 + 规则过滤，不依赖 LLM。
- 报告会在 GitHub Actions 中归档为 artifact，便于回看历史 Markdown。
- GitHub Actions 使用 4 个独立定时 workflow：工作日 08:37 盘前、14:07 基金操作提醒、16:37 盘后；周六/周日 09:37 周末量化周报。系统只允许在目标时间前后 5 分钟内发送，超窗会将任务标记为失败。
- 工作日会拆成两条钉钉消息：操作建议一条，资讯摘要一条。
- 各时间点推送内容做去重：盘前保留完整决策视图，14:00 只保留基金操作重点，盘后只保留收盘复盘和风险距离，周末保留周/月总结和资讯。
- GitHub Actions 运行失败时会尝试发送钉钉失败通知，附带 Actions 运行链接。

## 本地运行

```powershell
python -m pip install -r requirements.txt
Copy-Item config/watchlist.example.yml config/watchlist.yml
python -m stock_quant report --session premarket --config config/watchlist.yml --dry-run
python -m stock_quant report --session premarket --config config/watchlist.yml --dry-run --archive-dir reports --ledger-dir reports/ledger --dashboard-dir site
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
    market_value: 11000
    holding_pnl_amount: 1000
    holding_pnl_pct: 0.10
    target_weight: 0.20
    max_weight: 0.30
    risk_level: medium
    note: 核心基金
    thesis: 宽基修复持有，作为组合核心底仓
    thesis_risks:
      - 市场环境转为防守
      - 跌破中期均线后无法收复
    invalidation: 跌破风险位且连续两周信号偏弱
    proxy_symbol: "510300"
    proxy_name: 沪深300ETF
    proxy_asset_type: etf
    tags: ["持仓", "基金"]
```

`holding_amount` 建议填写累计投入本金。若你只有券商/基金 App 截图，也可以填写 `market_value`（当前市值）、`holding_pnl_amount`（持有盈亏金额）和 `holding_pnl_pct`（持有收益率，小数形式）。系统会优先使用截图字段生成组合市值、盈亏和持仓占比，并在缺少 `cost_price` 时按“最新净值 / (1 + 持有收益率)”反推成本净值。`target_weight` 和 `max_weight` 是组合目标仓位和上限仓位，用小数表示，例如 `0.20` 表示 20%。若基金名称仍是 `基金018044` 这类占位名，AKShare 可用时会尝试自动补全基金简称。

`thesis` / `thesis_risks` / `invalidation` 是可选的持仓逻辑字段，用来记录“为什么持有、主要担心什么、什么情况下原逻辑失效”。钉钉盘前报告只聚合显示逻辑状态，完整持仓逻辑放在可折叠看板中；若跌破风险位或信号转弱，会标记为“逻辑漂移”，但仍只作为人工复核提示，不会自动交易。

`proxy_symbol` / `proxy_name` / `proxy_asset_type` 是可选字段，用于 14:00 基金操作提醒的盘中估算。场外基金当天净值通常晚间更新，配置一个相关 ETF 或指数后，系统会用代理标的当日可见涨跌给出粗略估算；未配置时会退化为市场环境估算。

操作建议中的组合总览会基于 `market_value` / `holding_pnl_amount` / `holding_pnl_pct` 或 `holding_amount` / `cost_price` 估算组合市值、总盈亏、持仓占比和超仓提醒。若未配置持仓金额或截图市值，则只显示单标的信号。

数据新鲜度会显示最新行情日期、滞后标的和获取失败标的。场外基金净值可能有 T 日更新滞后，报告会把这类情况标出，避免用过期净值误判。

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

基金/ETF 候选会生成基金质量画像：质量分、近 1/3/6/12 月收益、最大回撤，并在 AKShare 对应数据可用时补充基金规模、基金经理任期、费率、同类排名和重仓集中度。外部接口不可用时不会中断日报，只显示能从行情推导出的指标。

A 股候选会在 AKShare 字段可用时生成基本面质量画像：ROE、毛利率、负债率、经营现金流覆盖、PE/PB、股息率、市值和成交额。它只作为候选排序的温和加分，仍会和趋势、回撤、市场环境一起综合判断，避免只按“便宜”或“涨得好”推荐。

操作建议和 14:00 基金提醒会附带“报告质检”区块。质检只做规则审计，用于发现过强交易措辞、收益承诺、缺少风险提示或免责声明；即使质检通过，也不代表建议一定正确。

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

回测摘要使用当前已获取的历史行情做轻量评估，输出覆盖标的数、平均区间收益、扣费后平均净收益、基准收益、平均超额、最大回撤和信号成功率。成本模型默认包含申购费、赎回费、双边滑点和调仓成本，可在配置里调整：

```yaml
backtest:
  buy_fee_rate: 0.001
  sell_fee_rate: 0.005
  slippage_rate: 0.001
  turnover_cost_rate: 0.001
  benchmark_symbol: sh000300
  benchmark_name: 沪深300
```

周末报告是“周末量化周报”：包含市场环境、本周持仓回顾、本周涨跌、本周最大回撤、月度复盘、自选外候选更新、相关资讯、风险事件日历和下周观察计划。周末报告不生成具体交易价位或即时卖出指令。

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

上传后可以在 Actions 页面手动触发 `Daily Quant Report`，或分别触发 `Premarket Quant Report`、`Fund Action Report`、`Postmarket Quant Report`、`Weekend Quant Report`，确认钉钉收到测试报告。

工作日 `premarket` / `postmarket` 会发送两条钉钉消息：

- 操作建议：市场环境、组合总览、数据新鲜度、回测摘要、自选标的紧凑信号、持仓成本/盈亏、持仓级建议、聚合逻辑状态、自选外候选观察、报告质检。
- 资讯摘要：相关新闻和摘要。

工作日 `fund_action` 的目标发送时间为北京时间 14:07，只包含自选基金/ETF，不包含股票、资讯或自选外候选。同一天成功发送后，后续同类触发会自动去重。

为降低 GitHub Actions 延迟或漏触发的影响，每个任务会在目标时间前 19、14、9、4 分钟和目标后 1 分钟冗余唤醒。较早启动的任务会先生成报告，再等待到目标时间前 5 分钟；每个钉钉请求发出前都会复核北京时间，超过目标时间后 5 分钟立即失败。钉钉网络超时会在窗口内有限重试，API 返回成功后立刻写入“北京时间日期 + session”发送回执，后续唤醒自动跳过。定时运行不执行测试套件，测试由代码提交时触发的 `Test Suite` workflow 独立完成。

GitHub 官方说明 `schedule` 事件可能因平台高负载而延迟，极端情况下排队任务可能被丢弃。因此本项目能严格阻止超窗消息并在超窗时报告失败，但仅使用 GitHub 托管调度无法提供基础设施级的绝对准点保证。手动触发 `workflow_dispatch` 不受发送时间窗和自动去重限制，方便测试。

如果测试、数据获取或发送步骤失败，workflow 会尝试发送一条“量化日报任务失败”到钉钉，消息里包含本次 GitHub Actions 运行链接，便于直接定位失败步骤。

每次成功生成报告后，workflow 会上传 `daily-quant-report-<session>-<date>` artifact，里面包含本次 Markdown 报告、结构化 JSON/CSV 台账和 `manifest.json`。台账会记录信号、候选、持仓逻辑复核、报告质检、候选质量画像等结构化字段，便于后续统计信号有效性。

静态看板会生成到 `site/`。由于你的报告里包含持仓成本和金额，workflow 默认不会发布 GitHub Pages。确认仓库已改为私有，或你接受公开展示这些信息后，再到仓库 `Settings -> Secrets and variables -> Actions -> Variables` 添加：

```text
ENABLE_PAGES=true
```

开启后，workflow 会用 GitHub Pages 发布当前看板，钉钉中的基金/股票名称和“完整图表”会链接到对应折叠面板；未开启时看板只保存在 Actions 运行产物里，钉钉不会显示网页链接。请先确认 Pages 的访问范围符合你的隐私要求，因为看板包含持仓金额、成本和盈亏。

手动触发时可选择：

- `premarket`：盘前量化日报。
- `fund_action`：14:00 基金操作提醒。
- `postmarket`：盘后量化复盘。
- `weekend_news`：周末量化周报。
