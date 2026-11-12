"""Consultas de usuários para autenticação local."""
import re
import secrets
import sqlite3
import time

from db import get_connection
from werkzeug.security import generate_password_hash

EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128
LOGIN_FAILURE_LIMIT = 5
LOGIN_WINDOW_SECONDS = 15 * 60


def get_user_by_username(database_path: str, username: str):
    username = username.strip().casefold()
    with get_connection(database_path) as connection:
        return connection.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()


def get_user_by_id(database_path: str, user_id: int, session_token: str | None):
    if not session_token:
        return None
    with get_connection(database_path) as connection:
        return connection.execute(
            "SELECT id, username, session_token FROM users WHERE id = ? AND session_token = ?",
            (user_id, session_token),
        ).fetchone()


def rotate_user_session(database_path: str, user_id: int) -> str:
    """Cria token de sessão de uso único; revoga sessões emitidas anteriormente."""
    token = secrets.token_urlsafe(32)
    with get_connection(database_path) as connection:
        connection.execute("UPDATE users SET session_token = ? WHERE id = ?", (token, user_id))
    return token


def login_is_rate_limited(database_path: str, remote_address: str, *, now: int | None = None) -> bool:
    now = int(time.time()) if now is None else now
    with get_connection(database_path) as connection:
        connection.execute("DELETE FROM auth_login_attempts WHERE attempted_at < ?", (now - 86400,))
        count = connection.execute(
            """SELECT COUNT(*) FROM auth_login_attempts
               WHERE remote_address = ? AND attempted_at >= ?""",
            (remote_address, now - LOGIN_WINDOW_SECONDS),
        ).fetchone()[0]
    return count >= LOGIN_FAILURE_LIMIT


def record_login_failure(database_path: str, remote_address: str, *, now: int | None = None) -> None:
    now = int(time.time()) if now is None else now
    with get_connection(database_path) as connection:
        connection.execute(
            "INSERT INTO auth_login_attempts (remote_address, attempted_at) VALUES (?, ?)",
            (remote_address, now),
        )


def clear_login_failures(database_path: str, remote_address: str) -> None:
    with get_connection(database_path) as connection:
        connection.execute(
            "DELETE FROM auth_login_attempts WHERE remote_address = ?", (remote_address,)
        )


def create_user(database_path: str, email: str, password: str,
                terms_version: str) -> int:
    """Cria uma conta usando o e-mail normalizado como identificador de login."""
    username = email.strip().casefold()
    if not EMAIL_PATTERN.fullmatch(username):
        raise ValueError("Informe um e-mail válido.")
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise ValueError("A senha deve ter entre 12 e 128 caracteres.")
    try:
        with get_connection(database_path) as connection:
            cursor = connection.execute(
                """INSERT INTO users
                   (username, password_hash, terms_accepted_at, terms_version)
                   VALUES (?, ?, CURRENT_TIMESTAMP, ?)""",
                (username, generate_password_hash(password), terms_version),
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        raise ValueError("Não foi possível criar a conta. Confira o e-mail e tente novamente.") from exc
