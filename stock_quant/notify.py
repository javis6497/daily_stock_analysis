from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
import urllib.parse
from typing import Any

import requests


def build_dingtalk_signed_url(
    webhook: str,
    secret: str | None,
    timestamp: int | None = None,
) -> str:
    if not secret:
        return webhook

    timestamp = timestamp if timestamp is not None else int(time.time() * 1000)
    string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), string_to_sign, hashlib.sha256).digest()
    sign = base64.b64encode(digest).decode("utf-8")
    separator = "&" if "?" in webhook else "?"
    return f"{webhook}{separator}{urllib.parse.urlencode({'timestamp': timestamp, 'sign': sign})}"


def build_dingtalk_markdown_payload(title: str, markdown: str) -> dict[str, Any]:
    return {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": markdown,
        },
    }


def send_dingtalk_markdown(
    title: str,
    markdown: str,
    webhook: str | None = None,
    secret: str | None = None,
    dry_run: bool = False,
    timeout: int = 10,
) -> dict[str, Any]:
    webhook = webhook or os.environ.get("DINGTALK_WEBHOOK")
    secret = secret if secret is not None else os.environ.get("DINGTALK_SECRET")
    payload = build_dingtalk_markdown_payload(title, markdown)

    if dry_run:
        return {"dry_run": True, "payload": payload}
    if not webhook:
        raise ValueError("DINGTALK_WEBHOOK is required when sending reports")

    response = requests.post(
        build_dingtalk_signed_url(webhook, secret),
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()
