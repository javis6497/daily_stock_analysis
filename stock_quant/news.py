from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import Instrument


@dataclass(frozen=True)
class NewsItem:
    title: str
    source: str
    url: str
    published_at: str
    summary: str = ""


def fetch_news(provider: str = "akshare", max_items: int = 50) -> list[NewsItem]:
    source = provider.lower()
    if source == "sample":
        return sample_news()[:max_items]
    if source == "akshare":
        return fetch_akshare_news(max_items)
    raise ValueError(f"unsupported news provider: {provider}")


def fetch_akshare_news(max_items: int = 50) -> list[NewsItem]:
    try:
        import akshare as ak
    except ModuleNotFoundError:
        return sample_news()[:max_items]

    source_specs = (
        (
            "东方财富",
            lambda: ak.stock_info_global_em(),
            ("标题",),
            ("摘要", "内容"),
            ("发布时间", "时间"),
            ("链接",),
        ),
        (
            "财联社",
            lambda: ak.stock_info_global_cls(symbol="全部"),
            ("标题",),
            ("内容", "摘要"),
            ("发布时间", "时间"),
            (),
        ),
        (
            "同花顺",
            lambda: ak.stock_info_global_ths(),
            ("标题",),
            ("内容", "摘要"),
            ("发布时间", "时间"),
            ("链接",),
        ),
    )
    items: list[NewsItem] = []
    seen_titles: set[str] = set()
    for source, loader, title_keys, summary_keys, time_keys, url_keys in source_specs:
        try:
            frame = loader()
        except Exception:
            continue
        for row in _iter_rows(frame):
            title = _first_text(row, title_keys)
            if not title or title in seen_titles:
                continue
            summary = _first_text(row, summary_keys)
            published_at = _published_at(row, time_keys)
            url = _first_text(row, url_keys)
            items.append(
                NewsItem(
                    title=title,
                    source=source,
                    url=url,
                    published_at=published_at,
                    summary=summary,
                )
            )
            seen_titles.add(title)
            if len(items) >= max_items:
                return items
    return items


def filter_news(
    items: Iterable[NewsItem],
    instruments: Iterable[Instrument],
    keywords: Iterable[str],
    max_items: int = 8,
) -> list[NewsItem]:
    tokens = [keyword for keyword in keywords if keyword]
    for instrument in instruments:
        tokens.append(instrument.name)
        tokens.append(instrument.symbol)

    items_list = list(items)
    if not tokens:
        return items_list[:max_items]

    scored: list[tuple[int, int, NewsItem]] = []
    for idx, item in enumerate(items_list):
        haystack = f"{item.title} {item.summary} {item.source}"
        score = sum(1 for token in tokens if token and token in haystack)
        scored.append((score, idx, item))
    scored.sort(key=lambda entry: (-entry[0], entry[1]))
    return [item for _, _, item in scored[:max_items]]


def sample_news() -> list[NewsItem]:
    return [
        NewsItem(
            title="政策利好推动宽基指数基金关注度提升",
            source="样例资讯",
            url="https://example.com/policy-index-fund",
            published_at="2026-07-03 08:00",
            summary="样例：政策和指数基金关注度变化。",
        ),
        NewsItem(
            title="市场成交回暖，资金继续关注高流动性 ETF",
            source="样例资讯",
            url="https://example.com/etf-flow",
            published_at="2026-07-03 08:15",
            summary="样例：资金继续关注高流动性产品。",
        ),
    ]


def _iter_rows(frame):
    if hasattr(frame, "iterrows"):
        for _, row in frame.iterrows():
            yield row
    else:
        yield from frame


def _first_text(row, keys: Iterable[str]) -> str:
    for key in keys:
        value = row.get(key) if hasattr(row, "get") else None
        if value is None:
            continue
        text = str(value).strip()
        if text and text.lower() != "nan":
            return text
    return ""


def _published_at(row, time_keys: Iterable[str]) -> str:
    published = _first_text(row, time_keys)
    date_part = _first_text(row, ("发布日期",))
    if date_part and published and date_part not in published:
        return f"{date_part} {published}"
    return published or date_part
