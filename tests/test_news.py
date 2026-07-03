from __future__ import annotations

import sys

from tests.helpers import make_instrument, require_module


class _FakeFrame:
    def __init__(self, rows):
        self._rows = rows

    def iterrows(self):
        for idx, row in enumerate(self._rows):
            yield idx, row


class _FakeAkShare:
    def stock_info_global_em(self):
        return _FakeFrame(
            [
                {
                    "标题": "A股政策预期升温，基金关注度提高",
                    "摘要": "市场关注政策方向",
                    "发布时间": "2026-07-04 09:00:00",
                    "链接": "https://example.com/em",
                }
            ]
        )

    def stock_info_global_cls(self, symbol="全部"):
        return _FakeFrame(
            [
                {
                    "标题": "公募基金调整权益仓位",
                    "内容": "机构关注成长方向",
                    "发布日期": "2026-07-04",
                    "发布时间": "09:05:00",
                }
            ]
        )


def test_fetch_akshare_news_normalizes_multiple_sources(monkeypatch):
    news = require_module("stock_quant.news")
    monkeypatch.setitem(sys.modules, "akshare", _FakeAkShare())

    items = news.fetch_news(provider="akshare", max_items=5)

    assert [item.source for item in items] == ["东方财富", "财联社"]
    assert items[0].title == "A股政策预期升温，基金关注度提高"
    assert items[0].summary == "市场关注政策方向"
    assert items[1].published_at == "2026-07-04 09:05:00"


def test_filter_news_prioritizes_keywords_and_falls_back_to_latest():
    news = require_module("stock_quant.news")
    items = [
        news.NewsItem("海外商品市场波动", "源", "", "2026-07-04 08:00"),
        news.NewsItem("基金经理关注A股政策", "源", "", "2026-07-04 09:00"),
    ]

    matched = news.filter_news(
        items,
        instruments=[make_instrument("018044", "基金018044", "fund")],
        keywords=["政策", "基金"],
        max_items=2,
    )

    assert matched[0].title == "基金经理关注A股政策"
    assert matched[1].title == "海外商品市场波动"
