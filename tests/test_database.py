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
                "SELECT username, password_hash FROM users WHERE username = 'admin'"
            ).fetchone()
            self.assertEqual(user["username"], "admin")
            self.assertNotEqual(user["password_hash"], "local-secret")
            self.assertTrue(check_password_hash(user["password_hash"], "local-secret"))

    def test_reinitialization_preserves_existing_data_and_password(self):
        initialize_database(self.database, self.schema, "admin", "first-secret")
        with get_connection(self.database) as connection:
            connection.execute(
                "INSERT INTO clients (name) VALUES (?)", ("Cliente de teste",))
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
        with self.assertRaises(sqlite3.IntegrityError):
            with get_connection(self.database) as connection:
                connection.execute(
                    "INSERT INTO quotes (client_id) VALUES (9999)")


if __name__ == "__main__":
    unittest.main()
