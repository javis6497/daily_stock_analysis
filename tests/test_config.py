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
watchlist:
  - symbol: "000001"
    name: 平安银行
    market: cn
    asset_type: stock
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
    assert app_config.candidate_pool[0].asset_type == "etf"
    assert app_config.news.provider == "akshare"
    assert app_config.news.keywords == ["政策", "基金"]


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
