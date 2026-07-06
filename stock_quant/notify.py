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
    result = response.json()
    if int(result.get("errcode", 0)) != 0:
        raise RuntimeError(
            f"DingTalk send failed: errcode={result.get('errcode')} errmsg={result.get('errmsg')}"
        )
    return result


def split_markdown_chunks(markdown: str, max_chars: int = 3500) -> list[str]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if len(markdown) <= max_chars:
        return [markdown]

    chunks: list[str] = []
    current = ""
    for line in markdown.split("\n"):
        candidate = line if not current else f"{current}\n{line}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = line
        while len(current) > max_chars:
            chunks.append(current[:max_chars])
            current = current[max_chars:]
    if current:
        chunks.append(current)
    return chunks


def send_dingtalk_markdown_chunks(
    title: str,
    markdown: str,
    webhook: str | None = None,
    secret: str | None = None,
    dry_run: bool = False,
    timeout: int = 10,
    max_chars: int = 3500,
) -> list[dict[str, Any]]:
    chunks = split_markdown_chunks(markdown, max_chars=max_chars)
    total = len(chunks)
    results: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks, start=1):
        chunk_title = title if total == 1 else f"{title} {index}/{total}"
        results.append(
            send_dingtalk_markdown(
                chunk_title,
                chunk,
                webhook=webhook,
                secret=secret,
                dry_run=dry_run,
                timeout=timeout,
            )
        )
    return results
