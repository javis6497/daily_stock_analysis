from __future__ import annotations

import base64
import hashlib
import hmac
import urllib.parse

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
