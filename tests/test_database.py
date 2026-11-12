"""Testes da inicialização e preservação do banco da Fase 1."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from werkzeug.security import check_password_hash

from db import get_connection, initialize_database


class DatabaseInitializationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "crm.sqlite3"
        self.schema = Path(__file__).resolve().parents[1] / "schema.sql"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_creates_all_tables_and_hashed_admin(self):
        initialize_database(self.database, self.schema, "admin", "local-secret")
        with get_connection(self.database) as connection:
            tables = {row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'")}
            self.assertTrue({"users", "clients", "products", "quotes", "quote_items"}
                            .issubset(tables))
            user = connection.execute(
                "SELECT username, password_hash, session_token FROM users WHERE username = 'admin'"
            ).fetchone()
            self.assertEqual(user["username"], "admin")
            self.assertNotEqual(user["password_hash"], "local-secret")
            self.assertTrue(check_password_hash(user["password_hash"], "local-secret"))
            self.assertIn("session_token", user.keys())

    def test_reinitialization_preserves_existing_data_and_password(self):
        initialize_database(self.database, self.schema, "admin", "first-secret")
        with get_connection(self.database) as connection:
            admin_id = connection.execute(
                "SELECT id FROM users WHERE username = 'admin'"
            ).fetchone()["id"]
            connection.execute(
                "INSERT INTO clients (user_id, name) VALUES (?, ?)",
                (admin_id, "Cliente de teste"),
            )
        initialize_database(self.database, self.schema, "admin", "changed-secret")
        with get_connection(self.database) as connection:
            client = connection.execute(
                "SELECT name FROM clients WHERE name = ?", ("Cliente de teste",)
            ).fetchone()
            user = connection.execute(
                "SELECT password_hash FROM users WHERE username = 'admin'").fetchone()
            self.assertIsNotNone(client)
            self.assertTrue(check_password_hash(user["password_hash"], "first-secret"))
            self.assertFalse(check_password_hash(user["password_hash"], "changed-secret"))

    def test_foreign_keys_are_enforced(self):
        initialize_database(self.database, self.schema, "admin", "local-secret")
        with get_connection(self.database) as connection:
            admin_id = connection.execute(
                "SELECT id FROM users WHERE username = 'admin'"
            ).fetchone()["id"]
        with self.assertRaises(sqlite3.IntegrityError):
            with get_connection(self.database) as connection:
                connection.execute(
                    "INSERT INTO quotes (user_id, client_id) VALUES (?, ?)", (admin_id, 9999))

    def test_existing_quotes_receive_client_snapshots_once(self):
        with get_connection(self.database) as connection:
            connection.executescript("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL DEFAULT '',
                    phone TEXT NOT NULL DEFAULT '',
                    company TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Enviado',
                    notes TEXT NOT NULL DEFAULT '',
                    total_cents INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT
                );
                INSERT INTO clients (name, email, phone, company)
                VALUES ('Cliente antigo', 'antigo@example.com', '111', 'Empresa antiga');
                INSERT INTO quotes (client_id, total_cents) VALUES (1, 7250);
            """)

        initialize_database(self.database, self.schema, "admin", "local-secret")
        with get_connection(self.database) as connection:
            admin_id = connection.execute(
                "SELECT id FROM users WHERE username = 'admin'"
            ).fetchone()["id"]
            owner_ids = {
                table: connection.execute(f"SELECT DISTINCT user_id FROM {table}").fetchone()[0]
                for table in ("clients", "quotes")
            }
            self.assertEqual(owner_ids, {"clients": admin_id, "quotes": admin_id})
            quote = connection.execute(
                "SELECT client_name, client_email, client_phone, client_company FROM quotes WHERE id = 1"
            ).fetchone()
            self.assertEqual(tuple(quote), (
                "Cliente antigo", "antigo@example.com", "111", "Empresa antiga"
            ))
            connection.execute(
                "UPDATE clients SET name = 'Cliente novo', email = 'novo@example.com' WHERE id = 1"
            )

        initialize_database(self.database, self.schema, "admin", "local-secret")
        with get_connection(self.database) as connection:
            quote = connection.execute(
                "SELECT client_name, client_email FROM quotes WHERE id = 1"
            ).fetchone()
            self.assertEqual(tuple(quote), ("Cliente antigo", "antigo@example.com"))

    def test_legacy_quotes_receive_medium_priority_and_migration_is_idempotent(self):
        with get_connection(self.database) as connection:
            connection.executescript("""
                CREATE TABLE clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL DEFAULT '',
                    phone TEXT NOT NULL DEFAULT '',
                    company TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Enviado',
                    notes TEXT NOT NULL DEFAULT '',
                    total_cents INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES clients(id)
                );
                INSERT INTO clients (name) VALUES ('Cliente legado');
                INSERT INTO quotes (client_id, status, notes, total_cents)
                VALUES (1, 'Aprovado', 'nota preservada', 12345);
            """)

        initialize_database(self.database, self.schema, "admin", "local-secret")
        with get_connection(self.database) as connection:
            quote = connection.execute(
                "SELECT id, status, notes, total_cents, priority FROM quotes WHERE id = 1"
            ).fetchone()
            self.assertEqual(tuple(quote), (1, "Aprovado", "nota preservada", 12345, "Média"))
            connection.execute("UPDATE quotes SET priority = 'Alta' WHERE id = 1")

        initialize_database(self.database, self.schema, "admin", "local-secret")
        with get_connection(self.database) as connection:
            quote = connection.execute(
                "SELECT id, status, notes, total_cents, priority FROM quotes WHERE id = 1"
            ).fetchone()
            self.assertEqual(tuple(quote), (1, "Aprovado", "nota preservada", 12345, "Alta"))

    def test_new_schema_defaults_priority_and_rejects_unknown_value(self):
        initialize_database(self.database, self.schema, "admin", "local-secret")
        with get_connection(self.database) as connection:
            admin_id = connection.execute(
                "SELECT id FROM users WHERE username = 'admin'"
            ).fetchone()["id"]
            client_id = connection.execute(
                "INSERT INTO clients (user_id, name) VALUES (?, 'Cliente')", (admin_id,)
            ).lastrowid
            quote_id = connection.execute(
                "INSERT INTO quotes (user_id, client_id) VALUES (?, ?)", (admin_id, client_id)
            ).lastrowid
            quote = connection.execute(
                "SELECT priority FROM quotes WHERE id = ?", (quote_id,)
            ).fetchone()
            self.assertEqual(quote["priority"], "Média")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE quotes SET priority = 'Urgente' WHERE id = ?", (quote_id,)
                )


if __name__ == "__main__":
    unittest.main()
