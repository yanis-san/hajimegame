"""Cloudflare Turnstile verification (the captcha on sign-up)."""

from __future__ import annotations

import httpx

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile(
    secret: str, token: str, ip: str, *, client: httpx.AsyncClient | None = None
) -> bool:
    """True when Cloudflare says the token is valid. Any network failure counts as a refusal."""
    if not token:
        return False
    try:
        if client is not None:
            response = await client.post(
                VERIFY_URL, data={"secret": secret, "response": token, "remoteip": ip}
            )
        else:
            async with httpx.AsyncClient(timeout=5.0) as own:
                response = await own.post(
                    VERIFY_URL, data={"secret": secret, "response": token, "remoteip": ip}
                )
        return bool(response.json().get("success"))
    except (httpx.HTTPError, ValueError):
        return False
