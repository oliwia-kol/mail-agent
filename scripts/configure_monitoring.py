"""Tworzy plik z hasłami i kluczami do lokalnego Langfuse."""

import os
from pathlib import Path
from secrets import token_hex

path = Path(__file__).resolve().parents[1] / ".env.langfuse"
values = {
    "LF_DB_PASSWORD": token_hex(24),
    "LF_REDIS_PASSWORD": token_hex(24),
    "LF_CLICKHOUSE_PASSWORD": token_hex(24),
    "LF_STORAGE_PASSWORD": token_hex(24),
    "LF_SALT": token_hex(24),
    "LF_ENCRYPTION_KEY": token_hex(32),
    "LF_AUTH_SECRET": token_hex(32),
    "LF_PUBLIC_KEY": "pk-lf-" + token_hex(16),
    "LF_SECRET_KEY": "sk-lf-" + token_hex(24),
    "LF_ADMIN_PASSWORD": token_hex(24),
}
try:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    raise SystemExit(
        ".env.langfuse już istnieje. Zachowano dotychczasowe hasła i klucze."
    ) from None
with os.fdopen(descriptor, "w") as file:
    file.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
print("Utworzono .env.langfuse. Hasło do panelu jest w polu LF_ADMIN_PASSWORD.")
