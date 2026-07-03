from __future__ import annotations

import sys

from tests.helpers import require_module


class _FakeFrame:
    def iterrows(self):
        yield 0, {"净值日期": "2026-07-01", "单位净值": 1.2345}


class _FakeAkShare:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def fund_open_fund_info_em(self, symbol: str, indicator: str):
        self.calls.append(("open_fund", symbol, indicator))
        return _FakeFrame()

    def fund_etf_hist_em(self, **_kwargs):
        raise AssertionError("open-end funds must not use the ETF history API")


def test_akshare_provider_uses_open_fund_nav_for_fund(monkeypatch):
    data = require_module("stock_quant.data")
    models = require_module("stock_quant.models")
    fake_akshare = _FakeAkShare()
    monkeypatch.setitem(sys.modules, "akshare", fake_akshare)

    bars = data.AkShareDataProvider().fetch_bars(
        models.Instrument("018044", "基金018044", "cn", "fund"),
        lookback_days=5,
    )

    assert fake_akshare.calls == [("open_fund", "018044", "单位净值走势")]
    assert bars[0].close == 1.2345


class _FakeNameFrame:
    def iterrows(self):
        yield 0, {"基金代码": "018044", "基金简称": "景顺长城纳斯达克科技ETF联接"}


class _FakeAkShareNames:
    def fund_name_em(self):
        return _FakeNameFrame()


def test_resolve_instrument_names_replaces_placeholder_fund_name(monkeypatch):
    data = require_module("stock_quant.data")
    models = require_module("stock_quant.models")
    monkeypatch.setitem(sys.modules, "akshare", _FakeAkShareNames())
    instrument = models.Instrument(
        "018044",
        "基金018044",
        "cn",
        "fund",
        cost_price=2.0,
        holding_amount=10000,
    )

    resolved = data.resolve_instrument_names("akshare", [instrument])

    assert resolved[0].name == "景顺长城纳斯达克科技ETF联接"
    assert resolved[0].cost_price == 2.0
    assert resolved[0].holding_amount == 10000.0
