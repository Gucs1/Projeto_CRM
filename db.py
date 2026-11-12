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
        admin = connection.execute(
            "SELECT id FROM users WHERE username = ? COLLATE NOCASE", (admin_username,)
        ).fetchone()
        migrate_user_terms(connection)
        migrate_quote_client_snapshots(connection)
        migrate_quote_priority(connection)
        migrate_user_ownership(connection, admin["id"])
        migrate_auth_security(connection)


def migrate_quote_client_snapshots(connection: sqlite3.Connection) -> None:
    """Adiciona snapshots de cliente a bancos já existentes sem apagar dados."""
    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(quotes)")
    }
    snapshot_columns = {
        "client_name": "TEXT NOT NULL DEFAULT ''",
        "client_email": "TEXT NOT NULL DEFAULT ''",
        "client_phone": "TEXT NOT NULL DEFAULT ''",
        "client_company": "TEXT NOT NULL DEFAULT ''",
    }
    for name, definition in snapshot_columns.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE quotes ADD COLUMN {name} {definition}")
            client_field = name.removeprefix("client_")
            connection.execute(
                f"""UPDATE quotes
                    SET {name} = COALESCE((
                        SELECT {client_field} FROM clients
                        WHERE clients.id = quotes.client_id
                    ), '')"""
            )


def migrate_quote_priority(connection: sqlite3.Connection) -> None:
    """Adiciona prioridade média aos orçamentos existentes sem alterar outros dados."""
    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(quotes)")
    }
    if "priority" not in columns:
        connection.execute(
            """ALTER TABLE quotes
               ADD COLUMN priority TEXT NOT NULL DEFAULT 'Média'
               CHECK (priority IN ('Baixa', 'Média', 'Alta'))"""
        )


def migrate_user_terms(connection: sqlite3.Connection) -> None:
    """Registra quando novas contas aceitam os termos, sem afetar usuários antigos."""
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)")}
    if "terms_accepted_at" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN terms_accepted_at TEXT")
    if "terms_version" not in columns:
        connection.execute(
            "ALTER TABLE users ADD COLUMN terms_version TEXT NOT NULL DEFAULT ''"
        )


def migrate_auth_security(connection: sqlite3.Connection) -> None:
    """Adiciona revogação de sessão e limite persistente sem descartar dados."""
    user_columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)")}
    if "session_token" not in user_columns:
        connection.execute("ALTER TABLE users ADD COLUMN session_token TEXT NOT NULL DEFAULT ''")
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS auth_login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            remote_address TEXT NOT NULL,
            attempted_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_auth_login_attempts_address_time
            ON auth_login_attempts(remote_address, attempted_at);
    """)


def migrate_user_ownership(connection: sqlite3.Connection, admin_id: int) -> None:
    """Dá os dados legados ao admin e adiciona guardas para bancos antigos."""
    for table in ("clients", "products", "quotes"):
        columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
        if "user_id" not in columns:
            connection.execute(
                f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"
            )
        connection.execute(
            f"UPDATE {table} SET user_id = ? WHERE user_id IS NULL", (admin_id,)
        )
        if table == "clients":
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_clients_user_name "
                "ON clients(user_id, name COLLATE NOCASE)"
            )
            connection.executescript("""
                CREATE TRIGGER IF NOT EXISTS clients_require_owner_insert
                BEFORE INSERT ON clients WHEN NEW.user_id IS NULL
                BEGIN SELECT RAISE(ABORT, 'client owner is required'); END;
                CREATE TRIGGER IF NOT EXISTS clients_require_owner_update
                BEFORE UPDATE OF user_id ON clients WHEN NEW.user_id IS NULL
                BEGIN SELECT RAISE(ABORT, 'client owner is required'); END;
            """)
        elif table == "products":
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_products_user_name "
                "ON products(user_id, name COLLATE NOCASE)"
            )
            connection.executescript("""
                CREATE TRIGGER IF NOT EXISTS products_require_owner_insert
                BEFORE INSERT ON products WHEN NEW.user_id IS NULL
                BEGIN SELECT RAISE(ABORT, 'product owner is required'); END;
                CREATE TRIGGER IF NOT EXISTS products_require_owner_update
                BEFORE UPDATE OF user_id ON products WHEN NEW.user_id IS NULL
                BEGIN SELECT RAISE(ABORT, 'product owner is required'); END;
            """)
        else:
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_quotes_user_client "
                "ON quotes(user_id, client_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_quotes_user_status "
                "ON quotes(user_id, status)"
            )
            connection.executescript("""
                CREATE TRIGGER IF NOT EXISTS quotes_require_owner_client_insert
                BEFORE INSERT ON quotes
                WHEN NEW.user_id IS NULL OR NOT EXISTS (
                    SELECT 1 FROM clients
                    WHERE clients.id = NEW.client_id AND clients.user_id = NEW.user_id
                )
                BEGIN SELECT RAISE(ABORT, 'quote owner and client must match'); END;
                CREATE TRIGGER IF NOT EXISTS quotes_require_owner_client_update
                BEFORE UPDATE OF user_id, client_id ON quotes
                WHEN NEW.user_id IS NULL OR NOT EXISTS (
                    SELECT 1 FROM clients
                    WHERE clients.id = NEW.client_id AND clients.user_id = NEW.user_id
                )
                BEGIN SELECT RAISE(ABORT, 'quote owner and client must match'); END;
                CREATE TRIGGER IF NOT EXISTS quote_items_require_owner_product_insert
                BEFORE INSERT ON quote_items
                WHEN NEW.product_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM quotes q JOIN products p ON p.user_id = q.user_id
                    WHERE q.id = NEW.quote_id AND p.id = NEW.product_id
                )
                BEGIN SELECT RAISE(ABORT, 'quote item product owner must match'); END;
                CREATE TRIGGER IF NOT EXISTS quote_items_require_owner_product_update
                BEFORE UPDATE OF quote_id, product_id ON quote_items
                WHEN NEW.product_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM quotes q JOIN products p ON p.user_id = q.user_id
                    WHERE q.id = NEW.quote_id AND p.id = NEW.product_id
                )
                BEGIN SELECT RAISE(ABORT, 'quote item product owner must match'); END;
            """)
