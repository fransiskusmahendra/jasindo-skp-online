from __future__ import annotations

import getpass
import hashlib
import secrets

ITERATIONS = 310_000

password = getpass.getpass("Password baru: ")
if len(password) < 10:
    raise SystemExit("Gunakan minimal 10 karakter.")
salt = secrets.token_bytes(16)
digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
print(f'password_salt = "{salt.hex()}"')
print(f'password_hash = "{digest.hex()}"')
