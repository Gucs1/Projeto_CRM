"""Testes do download autenticado e da geração paginada de propostas PDF."""
import re
import tempfile
import unittest
from pathlib import Path

from app import create_app, load_config
from db import get_connection
from models.quote import create_quote, get_quote
from pdf.generator import PriorityTag, generate_quote_pdf


class QuotePdfTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = str(Path(self.temp_dir.name) / "pdf.sqlite3")
        self.config = load_config()
        self.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": self.database_path,
            "SECRET_KEY": "pdf-test-session-secret",
        })
        with get_connection(self.database_path) as connection:
            self.user_id = connection.execute(
                "SELECT id FROM users WHERE username = ?", (self.config.ADMIN_USERNAME,)
            ).fetchone()["id"]
        self.client = self.app.test_client()
        login_page = self.client.get("/login")
        self.client.post("/login", data={
            "csrf_token": self.csrf_token(login_page),
            "username": self.config.ADMIN_USERNAME,
            "password": self.config.ADMIN_PASSWORD,
        })

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def csrf_token(response):
        match = re.search(
            r'type="hidden" name="csrf_token" value="([^"]+)"',
            response.get_data(as_text=True),
        )
        if not match:
            raise AssertionError("Token CSRF não encontrado")
        return match.group(1)

    def create_quote(self, *, description="Serviço de demonstração", notes="", priority="Média"):
        with get_connection(self.database_path) as connection:
            client_id = connection.execute(
                """INSERT INTO clients (user_id, name, email, phone, company)
                   VALUES (?, ?, ?, ?, ?)""",
                (self.user_id, "Cliente PDF", "cliente@example.test", "(11) 90000-0000", "Empresa PDF"),
            ).lastrowid
            product_id = connection.execute(
                """INSERT INTO products (user_id, name, description, unit_price_cents)
                   VALUES (?, ?, ?, ?)""",
                (self.user_id, "Serviço PDF", description, 15678),
            ).lastrowid
        quote_id = create_quote(
            self.database_path,
            self.user_id,
            client_id,
            notes,
            [{"product_id": product_id, "quantity": 2}],
            priority,
        )
        return quote_id

    def test_pdf_download_requires_login_and_has_automatic_filename(self):
        quote_id = self.create_quote(notes="Validade de 10 dias")
        anonymous = self.app.test_client()
        unauthenticated = anonymous.get(f"/quotes/{quote_id}/pdf")
        self.assertEqual(unauthenticated.status_code, 302)
        self.assertEqual(unauthenticated.headers["Location"], "/login")

        response = self.client.get(f"/quotes/{quote_id}/pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertEqual(
            response.headers["Content-Disposition"],
            f"attachment; filename=orcamento-{quote_id}.pdf",
        )
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertTrue(response.data.startswith(b"%PDF-"))
        self.assertGreater(len(response.data), 1500)

        detail = self.client.get(f"/quotes/{quote_id}")
        self.assertIn(f"/quotes/{quote_id}/pdf", detail.get_data(as_text=True))

    def test_pdf_fits_one_page_and_includes_replaceable_logo(self):
        quote_id = self.create_quote()
        result = get_quote(self.database_path, self.user_id, quote_id)
        logo_path = Path(self.temp_dir.name) / "logo.png"
        from PIL import Image
        Image.new("RGB", (360, 160), color=(37, 99, 235)).save(logo_path)

        pdf_bytes = generate_quote_pdf(
            result["quote"],
            result["items"],
            {"name": "Empresa Fictícia", "address": "Rua de Teste, 10",
             "phone": "(11) 5555-0000", "email": "contato@example.test"},
            logo_path,
        )
        pages = re.findall(rb"/Type\s*/Page\b", pdf_bytes)
        self.assertEqual(len(pages), 1)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_pdf_renders_the_selected_priority_tag(self):
        quote_id = self.create_quote(priority="Alta")
        result = get_quote(self.database_path, self.user_id, quote_id)
        rendered_priorities = []
        original_draw = PriorityTag.draw

        def capture_draw(tag):
            rendered_priorities.append(tag.priority)
            original_draw(tag)

        from unittest.mock import patch
        with patch.object(PriorityTag, "draw", capture_draw):
            pdf_bytes = generate_quote_pdf(
                result["quote"], result["items"], {"name": "Empresa Exemplo"}
            )

        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertEqual(rendered_priorities, ["Alta"])

    def test_long_description_and_notes_flow_across_multiple_pages(self):
        long_description = "Detalhe técnico de instalação e acompanhamento. " * 35
        long_notes = "Condições especiais, prazos e informações complementares. " * 35
        quote_id = self.create_quote(description=long_description, notes=long_notes)
        result = get_quote(self.database_path, self.user_id, quote_id)
        pdf_bytes = generate_quote_pdf(
            result["quote"],
            result["items"],
            {"name": "Empresa de Demonstração", "address": "São Paulo, SP",
             "phone": "(11) 5555-0000", "email": "contato@example.test"},
        )
        pages = re.findall(rb"/Type\s*/Page\b", pdf_bytes)
        self.assertGreater(len(pages), 1)
        self.assertLess(len(pages), 6)


if __name__ == "__main__":
    unittest.main()
