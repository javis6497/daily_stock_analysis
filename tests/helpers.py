from __future__ import annotations

import importlib
from datetime import date, timedelta

import pytest


def require_module(name: str):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as exc:
        pytest.fail(f"missing module {name}: {exc}")


def make_bars(direction: str = "up", count: int = 90):
    models = require_module("stock_quant.models")
    Bar = models.Bar

    bars = []
    start = date(2026, 1, 1)
    price = 10.0 if direction == "up" else 30.0
    step = 0.18 if direction == "up" else -0.16
    for idx in range(count):
        price = max(2.0, price + step)
        high = price + 0.35
        low = price - 0.35
        bars.append(
            Bar(
                date=start + timedelta(days=idx),
                open=price - 0.05,
                high=high,
                low=low,
                close=price,
                volume=1_000_000 + idx * 10_000,
            )
        )
    return bars


def make_instrument(symbol: str, name: str = "样例资产", asset_type: str = "stock"):
    models = require_module("stock_quant.models")
    return models.Instrument(
        symbol=symbol,
        name=name,
        market="cn",
        asset_type=asset_type,
        tags=["测试"],
    )
