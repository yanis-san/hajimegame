#!/usr/bin/env python3
"""Smoke test of a deployed site, from the outside, with the Python standard library only.

    python3 deploy/smoke.py https://hajime.yourdomain.com [--wait 90]

Checks what a visitor depends on: HTTPS with a valid certificate, the HTTP redirect, the pages in each language,
the security headers, a room created through the API, a WebSocket through the proxy, and that /metrics is not
public. Exit code 0 only if everything passes. The first checks are retried for --wait seconds because a fresh
deployment (and, the first time, the certificate request) needs a moment.
"""

from __future__ import annotations

import argparse
import base64
import http.client
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from urllib.parse import urlparse


class Check(Exception):
    pass


# --insecure (local tests against a self-signed certificate only): do not verify the certificate
TLS = ssl.create_default_context()


def fetch(
    url: str, *, method: str = "GET", headers: dict[str, str] | None = None, body: bytes | None = None
) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, method=method, headers=headers or {}, data=body)
    try:
        with urllib.request.urlopen(request, timeout=10, context=TLS) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()
    except urllib.error.HTTPError as error:
        return error.code, {k.lower(): v for k, v in error.headers.items()}, error.read()


def pin_address(hostname: str, address: str) -> None:
    """Make `hostname` resolve to `address` (the Host header and the TLS name stay the real ones)."""
    real = socket.getaddrinfo

    def patched(host, *args, **kwargs):  # type: ignore[no-untyped-def]
        return real(address if host == hostname else host, *args, **kwargs)

    socket.getaddrinfo = patched  # type: ignore[assignment]


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise Check(message)


def check_ready(base: str) -> None:
    status, _, body = fetch(f"{base}/readyz")
    expect(status == 200, f"/readyz answered {status}: {body[:200]!r}")
    expect(json.loads(body).get("status") == "ready", f"/readyz not ready: {body[:200]!r}")


def check_redirect(host: str) -> None:
    connection = http.client.HTTPConnection(host, timeout=10)
    connection.request("GET", "/")
    response = connection.getresponse()
    expect(response.status in (301, 302, 307, 308), f"http:// answered {response.status}, not a redirect")
    expect(
        (response.getheader("location") or "").startswith("https://"), "http:// does not redirect to https://"
    )


def check_pages(base: str) -> None:
    for path, lang in (("/", "fr"), ("/en", "en"), ("/ja", "ja")):
        status, headers, body = fetch(base + path, headers={"accept": "text/html"})
        expect(status == 200, f"{path} answered {status}")
        expect(f'lang="{lang}"'.encode() in body, f"{path} is not served in {lang}")
        expect("strict-transport-security" in headers, f"{path}: no HSTS header")
        expect(headers.get("x-content-type-options") == "nosniff", f"{path}: no nosniff")
        expect(headers.get("x-frame-options") == "DENY", f"{path}: framing is allowed")
        csp = headers.get("content-security-policy", "")
        expect("default-src 'none'" in csp and "'nonce-" in csp, f"{path}: missing or weak CSP")
        expect("unsafe-eval" not in csp, f"{path}: CSP allows eval")
        expect(b"Bakahatsu" in body, f"{path}: the page does not look like the game")


def check_metrics_private(base: str) -> None:
    status, _, _ = fetch(f"{base}/metrics")
    expect(status in (401, 404), f"/metrics is public (answered {status})")


def create_room(base: str) -> str:
    origin = base
    status, _, body = fetch(
        f"{base}/api/rooms",
        method="POST",
        headers={"origin": origin, "x-hajime-client": "web", "content-type": "application/json"},
        body=b"{}",
    )
    expect(status == 201, f"room creation answered {status}: {body[:200]!r}")
    room = json.loads(body)
    expect(len(room.get("code", "")) == 6, f"unexpected room: {room}")
    return str(room["ws_path"])


def check_websocket(base: str, path: str) -> None:
    parsed = urlparse(base)
    port = parsed.port or 443
    key = base64.b64encode(os.urandom(16)).decode()
    request = (
        f"GET {path} HTTP/1.1\r\nHost: {parsed.netloc}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\nOrigin: {base}\r\n\r\n"
    )
    with socket.create_connection((parsed.hostname or "", port), timeout=10) as raw:
        with TLS.wrap_socket(raw, server_hostname=parsed.hostname) as tls:
            tls.sendall(request.encode())
            first_line = tls.recv(1024).split(b"\r\n", 1)[0].decode(errors="replace")
    expect(" 101 " in first_line, f"WebSocket handshake through the proxy failed: {first_line!r}")


def retry(name: str, check: Callable[[], None], wait: float) -> str | None:
    deadline = time.monotonic() + wait
    while True:
        try:
            check()
            print(f"ok    {name}")
            return None
        except (Check, OSError, ValueError, KeyError) as error:
            if time.monotonic() >= deadline:
                print(f"FAIL  {name}: {error}")
                return f"{name}: {error}"
            time.sleep(3)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="https://your.domain")
    parser.add_argument("--wait", type=float, default=90, help="seconds to wait for the first checks")
    parser.add_argument("--insecure", action="store_true", help="accept a self-signed certificate (local tests only)")
    parser.add_argument("--resolve", metavar="IP", help="connect to this address instead of the DNS answer (test before the DNS record exists)")
    parser.add_argument("--no-redirect-check", action="store_true", help="skip the http:// redirect (local tests)")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    if not base.startswith("https://"):
        print("the site must be served over https://", file=sys.stderr)
        return 2
    host = urlparse(base).netloc
    if args.resolve:
        pin_address(urlparse(base).hostname or "", args.resolve)
    if args.insecure:
        TLS.check_hostname = False
        TLS.verify_mode = ssl.CERT_NONE

    failures: list[str | None] = []
    failures.append(retry("server ready (/readyz over HTTPS)", lambda: check_ready(base), args.wait))
    if not args.no_redirect_check:
        failures.append(retry("http:// redirects to https://", lambda: check_redirect(host), 10))
    failures.append(retry("pages in fr, en, ja with security headers", lambda: check_pages(base), 20))
    failures.append(retry("/metrics is not public", lambda: check_metrics_private(base), 10))
    room: list[str] = []
    failures.append(retry("a room can be created", lambda: room.append(create_room(base)), 20))
    if room:
        failures.append(retry("a WebSocket connects through the proxy", lambda: check_websocket(base, room[0]), 10))
    failed = [f for f in failures if f]
    print("\nall checks passed" if not failed else f"\n{len(failed)} check(s) failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
