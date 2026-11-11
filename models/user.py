"""Consultas de usuários para autenticação local."""
from db import get_connection


def get_user_by_username(database_path: str, username: str):
    with get_connection(database_path) as connection:
        return connection.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()


def get_user_by_id(database_path: str, user_id: int):
    with get_connection(database_path) as connection:
        return connection.execute(
            "SELECT id, username FROM users WHERE id = ?", (user_id,)
        ).fetchone()
