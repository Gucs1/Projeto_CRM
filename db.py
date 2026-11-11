"""Inicialização e acesso ao banco SQLite local."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from werkzeug.security import generate_password_hash


@contextmanager
def get_connection(database_path: str | Path) -> Iterator[sqlite3.Connection]:
    """Fornece uma conexão transacional e garante seu fechamento."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database(database_path: str | Path, schema_path: str | Path,
                        admin_username: str, admin_password: str) -> None:
    """Aplica o schema e cria o admin somente se ainda não existir."""
    schema = Path(schema_path).read_text(encoding="utf-8")
    with get_connection(database_path) as connection:
        connection.executescript(schema)
        existing = connection.execute(
            "SELECT id FROM users WHERE username = ?", (admin_username,)
        ).fetchone()
        if existing is None:
            connection.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (admin_username, generate_password_hash(admin_password)),
            )
