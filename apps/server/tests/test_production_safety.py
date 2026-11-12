from __future__ import annotations

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import AppSettings
from app.main import create_app

GOOD = {
    "env": "prod",
    "allowed_origins": ["https://hajime.dev"],
    "allow_missing_origin": False,
    "cookie_secure": True,
}


def test_a_proper_production_configuration_is_accepted() -> None:
    assert AppSettings(**GOOD).is_prod  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"allowed_origins": []}, "is empty"),
        ({"allowed_origins": ["http://hajime.dev"]}, "non-production origin"),
        ({"allowed_origins": ["https://localhost:3000"]}, "non-production origin"),
        ({"allowed_origins": ["https://hajime.example"]}, "non-production origin"),
        ({"allowed_origins": ["https://*.hajime.dev"]}, "non-production origin"),
        ({"allow_missing_origin": True}, "ALLOW_MISSING_ORIGIN"),
        ({"cookie_secure": False}, "COOKIE_SECURE"),
    ],
)
def test_an_unsafe_production_configuration_does_not_start(override: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        AppSettings(**{**GOOD, **override})  # type: ignore[arg-type]


def test_development_defaults_are_still_allowed() -> None:
    settings = AppSettings()
    assert not settings.is_prod
    assert settings.allow_missing_origin


async def metrics(settings: AppSettings, authorization: str | None = None) -> httpx.Response:
    app = create_app(settings)
    headers = {"authorization": authorization} if authorization else {}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.get("/metrics", headers=headers)


async def test_metrics_are_open_in_development() -> None:
    assert (await metrics(AppSettings())).status_code == 200


async def test_metrics_do_not_exist_in_production_without_a_token() -> None:
    assert (await metrics(AppSettings(**GOOD))).status_code == 404  # type: ignore[arg-type]


async def test_metrics_need_the_exact_token_when_one_is_set() -> None:
    settings = AppSettings(**GOOD, metrics_token="s3cret")  # type: ignore[arg-type]
    assert (await metrics(settings)).status_code == 401
    assert (await metrics(settings, "Bearer wrong")).status_code == 401
    assert (await metrics(settings, "Bearer s3cret")).status_code == 200
    assert "hajime_rooms_active" in (await metrics(settings, "Bearer s3cret")).text


def test_an_empty_optional_value_means_it_is_not_set() -> None:
    """docker compose passes an unset optional variable as an empty string."""
    settings = AppSettings(admin_password_hash="", admin_secret="", turnstile_secret=" ", database_url="")
    assert not settings.admin_enabled
    assert settings.turnstile_secret is None and settings.database_url is None
