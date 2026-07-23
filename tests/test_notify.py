from __future__ import annotations

import base64
import hashlib
import hmac
import urllib.parse

import pytest

from tests.helpers import require_module


def test_dingtalk_signed_url_uses_timestamp_secret_and_hmac_sha256():
    notify = require_module("stock_quant.notify")
    webhook = "https://oapi.dingtalk.com/robot/send?access_token=abc"
    secret = "SEC000000000000000000000"
    timestamp = 1_720_000_000_000

    signed_url = notify.build_dingtalk_signed_url(webhook, secret, timestamp=timestamp)
    parsed = urllib.parse.urlparse(signed_url)
    query = urllib.parse.parse_qs(parsed.query)
    expected_digest = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}\n{secret}".encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    expected_sign = urllib.parse.quote_plus(base64.b64encode(expected_digest))

    assert query["access_token"] == ["abc"]
    assert query["timestamp"] == [str(timestamp)]
    assert query["sign"] == [urllib.parse.unquote_plus(expected_sign)]


def test_build_dingtalk_markdown_payload_has_expected_shape():
    notify = require_module("stock_quant.notify")

    payload = notify.build_dingtalk_markdown_payload("日报", "## 内容")

    assert payload == {
        "msgtype": "markdown",
        "markdown": {"title": "日报", "text": "## 内容"},
    }


def test_split_markdown_chunks_preserves_text_and_limits_size():
    notify = require_module("stock_quant.notify")
    markdown = "\n".join([f"- 第 {idx} 行内容" for idx in range(30)])

    chunks = notify.split_markdown_chunks(markdown, max_chars=80)

    assert len(chunks) > 1
    assert all(len(chunk) <= 80 for chunk in chunks)
    assert "\n".join(chunks) == markdown


def test_send_dingtalk_markdown_raises_when_api_errcode_is_nonzero(monkeypatch):
    notify = require_module("stock_quant.notify")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"errcode": 310000, "errmsg": "message too long"}

    def fake_post(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(notify.requests, "post", fake_post)

    with pytest.raises(RuntimeError, match="DingTalk send failed"):
        notify.send_dingtalk_markdown(
            "日报",
            "内容",
            webhook="https://oapi.dingtalk.com/robot/send?access_token=test",
            secret="",
            max_attempts=1,
        )


def test_send_dingtalk_markdown_retries_transient_network_failure(monkeypatch):
    notify = require_module("stock_quant.notify")
    attempts = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"errcode": 0, "errmsg": "ok"}

    def fake_post(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise notify.requests.Timeout("temporary timeout")
        return FakeResponse()

    monkeypatch.setattr(notify.requests, "post", fake_post)
    monkeypatch.setattr(notify.time, "sleep", lambda _seconds: None)

    result = notify.send_dingtalk_markdown(
        "日报",
        "内容",
        webhook="https://oapi.dingtalk.com/robot/send?access_token=test",
        secret="",
        max_attempts=3,
    )

    assert len(attempts) == 2
    assert result["errcode"] == 0


def test_send_dingtalk_markdown_retries_transient_api_error(monkeypatch):
    notify = require_module("stock_quant.notify")
    attempts = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            attempts.append(1)
            if len(attempts) == 1:
                return {"errcode": 130101, "errmsg": "temporary busy"}
            return {"errcode": 0, "errmsg": "ok"}

    monkeypatch.setattr(notify.requests, "post", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(notify.time, "sleep", lambda _seconds: None)

    result = notify.send_dingtalk_markdown(
        "日报",
        "内容",
        webhook="https://oapi.dingtalk.com/robot/send?access_token=test",
        secret="",
        max_attempts=3,
    )

    assert len(attempts) == 2
    assert result["errcode"] == 0


def test_send_dingtalk_markdown_chunks_adds_part_numbers(monkeypatch):
    notify = require_module("stock_quant.notify")
    sent = []

    def fake_send(title, markdown, **kwargs):
        sent.append((title, markdown))
        return {"errcode": 0, "errmsg": "ok"}

    monkeypatch.setattr(notify, "send_dingtalk_markdown", fake_send)

    result = notify.send_dingtalk_markdown_chunks(
        "盘前操作建议",
        "第一段\n第二段\n第三段",
        max_chars=8,
        webhook="https://example.com",
    )

    assert len(result) > 1
    assert sent[0][0].startswith("盘前操作建议 1/")
    assert sent[-1][0].startswith(f"盘前操作建议 {len(sent)}/")


def test_send_dingtalk_markdown_chunks_uses_receipts_to_avoid_duplicates(monkeypatch, tmp_path):
    notify = require_module("stock_quant.notify")
    sent = []

    def fake_send(title, markdown, **kwargs):
        sent.append((title, markdown))
        return {"errcode": 0, "errmsg": "ok"}

    monkeypatch.setattr(notify, "send_dingtalk_markdown", fake_send)
    options = {
        "receipt_dir": tmp_path,
        "delivery_key": "premarket-2026-07-24-message-1",
        "webhook": "https://example.com",
    }

    first = notify.send_dingtalk_markdown_chunks("盘前操作建议", "内容", **options)
    second = notify.send_dingtalk_markdown_chunks("盘前操作建议", "内容已更新", **options)

    assert len(sent) == 1
    assert first[0]["errcode"] == 0
    assert second[0]["skipped"] is True
