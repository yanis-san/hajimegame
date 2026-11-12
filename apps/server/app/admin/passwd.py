"""Makes the three admin settings: ``uv run python -m app.admin.passwd``.

It asks for a password (not shown, not stored anywhere) and prints the lines to put in the server's
``.env``. The values are in single quotes because an Argon2 hash contains ``$``, which a ``.env`` file
would otherwise expand."""

from __future__ import annotations

import getpass
import secrets
import sys

from argon2 import PasswordHasher

MIN_LENGTH = 12


def main() -> int:
    password = getpass.getpass(f"Admin password (at least {MIN_LENGTH} characters): ")
    if len(password) < MIN_LENGTH:
        print(f"Too short: use at least {MIN_LENGTH} characters.", file=sys.stderr)
        return 1
    if getpass.getpass("Again: ") != password:
        print("The two passwords differ.", file=sys.stderr)
        return 1
    print("\nAdd these lines to /opt/hajime/.env on the server (then deploy again):\n")
    print("HAJIME_ADMIN_USERNAME=admin")
    print(f"HAJIME_ADMIN_PASSWORD_HASH='{PasswordHasher().hash(password)}'")
    print(f"HAJIME_ADMIN_SECRET='{secrets.token_urlsafe(48)}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
