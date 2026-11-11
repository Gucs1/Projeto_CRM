"""Testes de orçamento, recálculo, snapshots, status e histórico."""
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app, load_config
from db import get_connection
from models.quote import create_quote, get_dashboard_data, get_quote


class QuoteFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = str(Path(self.temp_dir.name) / "quotes.sqlite3")
        self.local_config = load_config()
        self.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.database_path,
            "SECRET_KEY": "quote-test-secret",
        })
        self.client = self.app.test_client()
        login_page = self.client.get("/login")
        self.client.post("/login", data={
            "csrf_token": self.csrf_token(login_page),
            "username": self.local_config.ADMIN_USERNAME,
            "password": self.local_config.ADMIN_PASSWORD,
        })

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def csrf_token(response) -> str:
        match = re.search(
            r'type="hidden" name="csrf_token" value="([^"]+)"',
            response.get_data(as_text=True),
        )
        if not match:
            raise AssertionError("Token CSRF não encontrado")
        return match.group(1)

    def create_client(self, name="Cliente de Teste", **overrides) -> int:
        values = {
            "name": name,
            "email": overrides.get("email", "cliente@example.com"),
            "phone": overrides.get("phone", "(11) 90000-0000"),
            "company": overrides.get("company", "Empresa Original"),
            "notes": "",
        }
        with get_connection(self.database_path) as connection:
            cursor = connection.execute(
                """INSERT INTO clients (name, email, phone, company, notes)
                   VALUES (:name, :email, :phone, :company, :notes)""",
                values,
            )
            return cursor.lastrowid

    def create_product(self, name="Serviço Original", price=12550, description="Descrição original") -> int:
        with get_connection(self.database_path) as connection:
            cursor = connection.execute(
                """INSERT INTO products (name, description, unit_price_cents)
                   VALUES (?, ?, ?)""",
                (name, description, price),
            )
            return cursor.lastrowid

    def post_with_csrf(self, get_path, post_path, values):
        page = self.client.get(get_path)
        return self.client.post(
            post_path,
            data={**values, "csrf_token": self.csrf_token(page)},
        )

    def test_new_quote_prompts_for_missing_catalog(self):
        response = self.client.get("/quotes/new")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Prepare seus cadastros primeiro", body)
        self.assertIn("Cadastrar cliente", body)
        self.assertIn("Cadastrar produto ou serviço", body)

    def test_create_recalculates_total_and_preserves_client_and_item_snapshots(self):
        client_id = self.create_client()
        product_id = self.create_product()
        second_product_id = self.create_product(
            "Instalação", 2500, "Instalação padrão"
        )
        values = {
            "client_id": str(client_id),
            "product_id": [str(product_id), str(second_product_id)],
            "quantity": ["2", "3"],
            "notes": "Validade de 15 dias",
            # Estes valores adulterados não são usados pelo servidor.
            "unit_price_cents": ["1", "1"],
            "total_cents": "1",
        }
        response = self.post_with_csrf("/quotes/new", "/quotes/new", values)
        self.assertEqual(response.status_code, 302)
        quote_id = int(response.headers["Location"].rsplit("/", 1)[-1])

        result = get_quote(self.database_path, quote_id)
        self.assertEqual(result["quote"]["status"], "Enviado")
        self.assertEqual(result["quote"]["total_cents"], 25_100 + 7_500)
        self.assertEqual(result["quote"]["notes"], "Validade de 15 dias")
        self.assertEqual(result["quote"]["client_name"], "Cliente de Teste")
        self.assertEqual(result["quote"]["client_email"], "cliente@example.com")
        self.assertEqual([item["line_total_cents"] for item in result["items"]], [25_100, 7_500])
        self.assertEqual(result["items"][0]["unit_price_cents"], 12_550)

        with get_connection(self.database_path) as connection:
            connection.execute(
                "UPDATE clients SET name = ?, email = ?, company = ? WHERE id = ?",
                ("Cliente Atualizado", "novo@example.com", "Empresa Nova", client_id),
            )
            connection.execute(
                """UPDATE products SET name = ?, description = ?, unit_price_cents = ?
                   WHERE id = ?""",
                ("Serviço Atualizado", "Descrição atualizada", 99_900, product_id),
            )

        detail = self.client.get(f"/quotes/{quote_id}")
        body = detail.get_data(as_text=True)
        self.assertEqual(detail.status_code, 200)
        self.assertIn("Cliente de Teste", body)
        self.assertIn("cliente@example.com", body)
        self.assertIn("Serviço Original", body)
        self.assertIn("Descrição original", body)
        self.assertIn("R$ 125,50", body)
        self.assertNotIn("Serviço Atualizado", body)
        self.assertNotIn("novo@example.com", body)

        history = self.client.get(f"/clients/{client_id}/quotes")
        self.assertEqual(history.status_code, 200)
        self.assertIn("Cliente Atualizado", history.get_data(as_text=True))
        self.assertIn(f"#{quote_id}", history.get_data(as_text=True))

    def test_quantities_and_catalog_ids_are_validated_without_partial_quotes(self):
        client_id = self.create_client()
        product_id = self.create_product()
        for quantity in ("0", "-1", "1.5", "1000001"):
            with self.subTest(quantity=quantity):
                response = self.post_with_csrf("/quotes/new", "/quotes/new", {
                    "client_id": str(client_id),
                    "product_id": [str(product_id)],
                    "quantity": [quantity],
                    "notes": "",
                })
                self.assertEqual(response.status_code, 422)

        response = self.post_with_csrf("/quotes/new", "/quotes/new", {
            "client_id": str(client_id),
            "product_id": ["99999"],
            "quantity": ["1"],
            "notes": "",
        })
        self.assertEqual(response.status_code, 422)
        with get_connection(self.database_path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM quotes").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM quote_items").fetchone()[0], 0)

    def test_quote_and_items_are_rolled_back_together_on_item_failure(self):
        client_id = self.create_client()
        first_product_id = self.create_product()
        second_product_id = self.create_product("Produto recusado", 500)
        with get_connection(self.database_path) as connection:
            connection.execute(
                f"""CREATE TRIGGER reject_second_quote_item
                    BEFORE INSERT ON quote_items
                    WHEN NEW.product_id = {second_product_id}
                    BEGIN SELECT RAISE(ABORT, 'item insert failed'); END"""
            )

        with self.assertRaises(sqlite3.IntegrityError):
            create_quote(self.database_path, client_id, "", [
                {"product_id": first_product_id, "quantity": 1},
                {"product_id": second_product_id, "quantity": 1},
            ])
        with get_connection(self.database_path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM quotes").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM quote_items").fetchone()[0], 0)

    def test_status_changes_drive_dashboard_counts_and_validate_values(self):
        client_id = self.create_client()
        product_id = self.create_product()
        response = self.post_with_csrf("/quotes/new", "/quotes/new", {
            "client_id": str(client_id),
            "product_id": [str(product_id)],
            "quantity": ["1"],
            "notes": "",
        })
        quote_id = int(response.headers["Location"].rsplit("/", 1)[-1])
        detail = f"/quotes/{quote_id}"

        bad_status = self.post_with_csrf(detail, f"{detail}/status", {"status": "Apagado"})
        self.assertEqual(bad_status.status_code, 302)
        self.assertEqual(get_quote(self.database_path, quote_id)["quote"]["status"], "Enviado")

        approved = self.post_with_csrf(detail, f"{detail}/status", {"status": "Aprovado"})
        self.assertEqual(approved.status_code, 302)
        approved_page = self.client.get(detail)
        self.assertIn("bg-emerald-50", approved_page.get_data(as_text=True))
        with get_connection(self.database_path) as connection:
            connection.execute(
                "INSERT INTO quotes (client_id, client_name, status, total_cents) VALUES (?, ?, ?, ?)",
                (client_id, "Cliente de Teste", "Recusado", 100),
            )

        dashboard = self.client.get("/")
        body = dashboard.get_data(as_text=True)
        self.assertIn("Criados", body)
        self.assertIn("Aprovados", body)
        self.assertIn("Recusados", body)
        counts = get_dashboard_data(self.database_path)["counts"]
        self.assertEqual(counts, {"total": 2, "approved": 1, "declined": 1})

        declined = self.post_with_csrf(detail, f"{detail}/status", {"status": "Recusado"})
        self.assertEqual(declined.status_code, 302)
        self.assertEqual(get_quote(self.database_path, quote_id)["quote"]["status"], "Recusado")


if __name__ == "__main__":
    unittest.main()
