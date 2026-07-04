from __future__ import annotations

from tests.helpers import require_module


def test_load_config_parses_watchlist_and_defaults(tmp_path):
    config_mod = require_module("stock_quant.config")
    config_path = tmp_path / "watchlist.yml"
    config_path.write_text(
        """
timezone: Asia/Shanghai
data:
  provider: sample
report:
  top_n: 2
recommendation:
  include_dynamic_a_shares: true
  include_dynamic_etfs: true
  dynamic_a_share_limit: 12
  dynamic_etf_limit: 9
  min_turnover: 600000000
  min_etf_turnover: 120000000
  min_market_cap: 60000000000
  max_pe: 60
  max_pb: 8
  max_candidate_single_day_pct: 0.06
  max_candidates_per_group: 1
watchlist:
  - symbol: "000001"
    name: 平安银行
    market: cn
    asset_type: stock
    cost_price: 10.5
    holding_amount: 12000
    target_weight: 0.25
    max_weight: 0.35
    risk_level: medium
    note: 核心持仓
candidate_pool:
  - symbol: "510300"
    name: 沪深300ETF
    market: cn
    asset_type: etf
news:
  provider: akshare
  keywords: ["政策", "基金"]
""",
        encoding="utf-8",
    )

    app_config = config_mod.load_config(config_path)

    assert app_config.timezone == "Asia/Shanghai"
    assert app_config.data.provider == "sample"
    assert app_config.report.top_n == 2
    assert app_config.watchlist[0].symbol == "000001"
    assert app_config.watchlist[0].cost_price == 10.5
    assert app_config.watchlist[0].holding_amount == 12000.0
    assert app_config.watchlist[0].target_weight == 0.25
    assert app_config.watchlist[0].max_weight == 0.35
    assert app_config.watchlist[0].risk_level == "medium"
    assert app_config.watchlist[0].note == "核心持仓"
    assert app_config.candidate_pool[0].asset_type == "etf"
    assert app_config.news.provider == "akshare"
    assert app_config.news.keywords == ["政策", "基金"]
    assert app_config.recommendation.enabled is True
    assert app_config.recommendation.include_dynamic_a_shares is True
    assert app_config.recommendation.include_dynamic_etfs is True
    assert app_config.recommendation.dynamic_a_share_limit == 12
    assert app_config.recommendation.dynamic_etf_limit == 9
    assert app_config.recommendation.min_turnover == 600_000_000
    assert app_config.recommendation.min_etf_turnover == 120_000_000
    assert app_config.recommendation.min_market_cap == 60_000_000_000
    assert app_config.recommendation.max_pe == 60
    assert app_config.recommendation.max_pb == 8
    assert app_config.recommendation.max_candidate_single_day_pct == 0.06
    assert app_config.recommendation.max_candidates_per_group == 1


def test_load_config_rejects_empty_watchlist(tmp_path):
    config_mod = require_module("stock_quant.config")
    config_path = tmp_path / "watchlist.yml"
    config_path.write_text("watchlist: []\n", encoding="utf-8")

    try:
        config_mod.load_config(config_path)
    except ValueError as exc:
        assert "watchlist" in str(exc)
    else:
        raise AssertionError("empty watchlist should be rejected")
