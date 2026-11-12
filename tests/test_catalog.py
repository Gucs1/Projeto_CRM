"""Testes dos cadastros de clientes e produtos/serviços."""
import re
import tempfile
import unittest
from pathlib import Path

from app import create_app, load_config
from db import get_connection


class CatalogCrudTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = str(Path(self.temp_dir.name) / "catalog.sqlite3")
        self.local_config = load_config()
        self.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.database_path,
            "SECRET_KEY": "catalog-test-secret",
        })
        with get_connection(self.database_path) as connection:
            self.user_id = connection.execute(
                "SELECT id FROM users WHERE username = ?", (self.local_config.ADMIN_USERNAME,)
            ).fetchone()["id"]
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
            raise AssertionError("Token CSRF não encontrado na página")
        return match.group(1)

    def client_values(self, **overrides):
        values = {
            "name": "Maria Silva",
            "email": "maria@example.com",
            "phone": "(11) 99999-1234",
            "company": "Exemplo Ltda.",
            "notes": "Contato comercial",
        }
        values.update(overrides)
        return values

    def create_client(self, **values) -> int:
        with get_connection(self.database_path) as connection:
            cursor = connection.execute(
                """INSERT INTO clients (user_id, name, email, phone, company, notes)
                   VALUES (:user_id, :name, :email, :phone, :company, :notes)""",
                {**self.client_values(**values), "user_id": self.user_id},
            )
            return cursor.lastrowid

    def product_values(self, **overrides):
        values = {
            "name": "Consultoria",
            "description": "Acompanhamento mensal",
            "unit_price": "1.234,56",
        }
        values.update(overrides)
        return values

    def create_product(self, name="Consultoria", price_cents=123456) -> int:
        with get_connection(self.database_path) as connection:
            cursor = connection.execute(
                """INSERT INTO products (user_id, name, description, unit_price_cents)
                   VALUES (?, ?, ?, ?)""",
                (self.user_id, name, "Acompanhamento mensal", price_cents),
            )
            return cursor.lastrowid

    def csrf_post(self, path, values):
        page = self.client.get("/")
        token = self.csrf_token(page)
        return self.client.post(path, data={**values, "csrf_token": token})

    def test_client_create_search_edit_and_validation(self):
        response = self.client.get("/clients")
        self.assertEqual(response.status_code, 200)
        form = self.client.get("/clients/new")
        response = self.client.post("/clients/new", data={
            **self.client_values(), "csrf_token": self.csrf_token(form),
        })
        self.assertEqual(response.status_code, 302)

        with get_connection(self.database_path) as connection:
            connection.execute(
                "INSERT INTO clients (user_id, name, email) VALUES (?, ?, ?)",
                (self.user_id, "Carlos Dias", "carlos@example.com"),
            )
        response = self.client.get("/clients?q=maria")
        body = response.get_data(as_text=True)
        self.assertIn("Maria Silva", body)
        self.assertNotIn("Carlos Dias", body)

        with get_connection(self.database_path) as connection:
            connection.executemany(
                "INSERT INTO clients (user_id, name) VALUES (?, ?)",
                [(self.user_id, "100% Projetos"), (self.user_id, "1000 Projetos")],
            )
        escaped_search = self.client.get("/clients", query_string={"q": "%"})
        escaped_body = escaped_search.get_data(as_text=True)
        self.assertIn("100% Projetos", escaped_body)
        self.assertNotIn("1000 Projetos", escaped_body)

        client_id = 1
        edit_page = self.client.get(f"/clients/{client_id}/edit")
        response = self.client.post(f"/clients/{client_id}/edit", data={
            **self.client_values(name="Maria de Souza", email="maria.souza@example.com"),
            "csrf_token": self.csrf_token(edit_page),
        })
        self.assertEqual(response.status_code, 302)
        with get_connection(self.database_path) as connection:
            updated = connection.execute(
                "SELECT name, email FROM clients WHERE id = ?", (client_id,)
            ).fetchone()
        self.assertEqual(updated["name"], "Maria de Souza")
        self.assertEqual(updated["email"], "maria.souza@example.com")

        form = self.client.get("/clients/new")
        response = self.client.post("/clients/new", data={
            **self.client_values(name="   "), "csrf_token": self.csrf_token(form),
        })
        self.assertEqual(response.status_code, 422)
        self.assertIn("Informe o nome do cliente", response.get_data(as_text=True))
        self.assertIn('aria-invalid="true"', response.get_data(as_text=True))
        self.assertIn('id="name-error"', response.get_data(as_text=True))

        form = self.client.get("/clients/new")
        response = self.client.post("/clients/new", data={
            **self.client_values(email="não-é-email"), "csrf_token": self.csrf_token(form),
        })
        self.assertEqual(response.status_code, 422)

    def test_catalog_routes_require_login(self):
        anonymous = self.app.test_client()
        for path in (
            "/clients", "/clients/new", "/products", "/products/new",
            "/quotes", "/quotes/new", "/clients/1/quotes",
        ):
            with self.subTest(path=path):
                response = anonymous.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.headers["Location"], "/login")

    def test_client_delete_requires_csrf_and_blocks_quote_reference(self):
        client_id = self.create_client()
        self.assertEqual(self.client.post(f"/clients/{client_id}/delete").status_code, 400)
        with get_connection(self.database_path) as connection:
            connection.execute(
                "INSERT INTO quotes (user_id, client_id) VALUES (?, ?)",
                (self.user_id, client_id),
            )

        response = self.csrf_post(f"/clients/{client_id}/delete", {})
        self.assertEqual(response.status_code, 302)
        listing = self.client.get("/clients")
        self.assertEqual(listing.status_code, 200)
        self.assertIn("vinculado a um orçamento", listing.get_data(as_text=True))
        with get_connection(self.database_path) as connection:
            self.assertIsNotNone(connection.execute(
                "SELECT id FROM clients WHERE id = ?", (client_id,)
            ).fetchone())
        with get_connection(self.database_path) as connection:
            connection.execute("DELETE FROM quotes WHERE client_id = ?", (client_id,))
        response = self.csrf_post(f"/clients/{client_id}/delete", {})
        self.assertEqual(response.status_code, 302)
        with get_connection(self.database_path) as connection:
            self.assertIsNone(connection.execute(
                "SELECT id FROM clients WHERE id = ?", (client_id,)
            ).fetchone())

    def test_product_create_edit_price_validation_and_delete(self):
        form = self.client.get("/products/new")
        response = self.client.post("/products/new", data={
            **self.product_values(), "csrf_token": self.csrf_token(form),
        })
        self.assertEqual(response.status_code, 302)
        with get_connection(self.database_path) as connection:
            product = connection.execute(
                "SELECT id, unit_price_cents FROM products WHERE name = ?",
                ("Consultoria",),
            ).fetchone()
        self.assertEqual(product["unit_price_cents"], 123456)
        listing = self.client.get("/products")
        self.assertIn("R$ 1.234,56", listing.get_data(as_text=True))

        product_id = product["id"]
        edit_page = self.client.get(f"/products/{product_id}/edit")
        response = self.client.post(f"/products/{product_id}/edit", data={
            **self.product_values(name="Consultoria premium", unit_price="59.90"),
            "csrf_token": self.csrf_token(edit_page),
        })
        self.assertEqual(response.status_code, 302)
        with get_connection(self.database_path) as connection:
            updated = connection.execute(
                "SELECT name, unit_price_cents FROM products WHERE id = ?",
                (product_id,),
            ).fetchone()
        self.assertEqual(updated["name"], "Consultoria premium")
        self.assertEqual(updated["unit_price_cents"], 5990)

        form = self.client.get("/products/new")
        response = self.client.post("/products/new", data={
            **self.product_values(unit_price="-2,00"), "csrf_token": self.csrf_token(form),
        })
        self.assertEqual(response.status_code, 422)
        form = self.client.get("/products/new")
        response = self.client.post("/products/new", data={
            **self.product_values(unit_price="1,239"), "csrf_token": self.csrf_token(form),
        })
        self.assertEqual(response.status_code, 422)
        form = self.client.get("/products/new")
        response = self.client.post("/products/new", data={
            **self.product_values(unit_price="999999999999999999999999"),
            "csrf_token": self.csrf_token(form),
        })
        self.assertEqual(response.status_code, 422)
        body = response.get_data(as_text=True)
        self.assertIn('id="unit-price-error"', body)
        self.assertIn('aria-describedby="unit-price-error"', body)

        response = self.csrf_post(f"/products/{product_id}/delete", {})
        self.assertEqual(response.status_code, 302)
        with get_connection(self.database_path) as connection:
            self.assertIsNone(connection.execute(
                "SELECT id FROM products WHERE id = ?", (product_id,)
            ).fetchone())

    def test_product_delete_blocks_quote_item_reference(self):
        product_id = self.create_product()
        client_id = self.create_client()
        with get_connection(self.database_path) as connection:
            quote_id = connection.execute(
                "INSERT INTO quotes (user_id, client_id, total_cents) VALUES (?, ?, ?)",
                (self.user_id, client_id, 123456),
            ).lastrowid
            connection.execute(
                """INSERT INTO quote_items
                   (quote_id, product_id, product_name, description, quantity,
                    unit_price_cents, line_total_cents)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (quote_id, product_id, "Consultoria", "Acompanhamento mensal", 1, 123456, 123456),
            )
        response = self.csrf_post(f"/products/{product_id}/delete", {})
        self.assertEqual(response.status_code, 302)
        listing = self.client.get("/products")
        self.assertIn("vinculado a um orçamento", listing.get_data(as_text=True))
        with get_connection(self.database_path) as connection:
            self.assertIsNotNone(connection.execute(
                "SELECT id FROM products WHERE id = ?", (product_id,)
            ).fetchone())


if __name__ == "__main__":
    unittest.main()
