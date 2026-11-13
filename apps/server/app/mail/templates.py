"""The e-mails the site sends, in the three interface languages."""

from __future__ import annotations

SITE = "Bakahatsu"

LANGUAGES = ("fr", "en", "ja")


def verification(lang: str, username: str, link: str, hours: int) -> tuple[str, str]:
    """(subject, body) of the message that confirms an e-mail address."""
    if lang == "en":
        return (
            f"Confirm your email · {SITE}",
            f"Hi {username},\n\n"
            f"Confirm your email address for your {SITE} account by opening this link:\n\n{link}\n\n"
            f"The link works once and for {hours} hours.\n\n"
            "If you did not create this account, you can ignore this message: nothing will happen.\n",
        )
    if lang == "ja":
        return (
            f"メールアドレスの確認 · {SITE}",
            f"{username} さん\n\n"
            f"{SITE} のアカウントのメールアドレスを確認するには、次のリンクを開いてください。\n\n{link}\n\n"
            f"このリンクは1回だけ、{hours}時間有効です。\n\n"
            "このアカウントを作成した覚えがない場合は、このメッセージを無視してください。何も起こりません。\n",
        )
    return (
        f"Confirme ton email · {SITE}",
        f"Bonjour {username},\n\n"
        f"Confirme l’adresse email de ton compte {SITE} en ouvrant ce lien :\n\n{link}\n\n"
        f"Le lien ne marche qu’une fois, pendant {hours} heures.\n\n"
        "Si tu n’as pas créé ce compte, ignore ce message : il ne se passera rien.\n",
    )
