"""Valida login, proteção de rotas, CSRF e abertura local do navegador."""
import re
import io
import tempfile
import unittest
from contextlib import nullcontext, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import runpy

import app as crm_app
from app import create_app, load_config, open_browser_when_ready, run_local


class AuthAndInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = load_config()
        self.app = create_app({
            "TESTING": True,
            "DATABASE_PATH": str(Path(self.temp_dir.name) / "crm-test.sqlite3"),
            "SECRET_KEY": "test-session-secret",
            "WTF_CSRF_ENABLED": True,
            "AUTO_OPEN_BROWSER": False,
        })
        self.client = self.app.test_client()

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

    def test_protected_page_redirects_to_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")

    def test_stale_session_does_not_grant_access(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 9999
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)

    def test_first_run_config_is_private_persistent_and_shows_password_once(self):
        config_path = Path(self.temp_dir.name) / "config.py"
        output = io.StringIO()
        with patch.object(crm_app, "CONFIG_PATH", config_path):
            with redirect_stdout(output):
                crm_app.ensure_local_config()
            first_contents = config_path.read_text(encoding="utf-8")
            generated = runpy.run_path(str(config_path))
            with redirect_stdout(output):
                crm_app.ensure_local_config()
        self.assertEqual(config_path.read_text(encoding="utf-8"), first_contents)
        self.assertEqual(generated["ADMIN_USERNAME"], "admin")
        self.assertEqual(len(generated["ADMIN_PASSWORD"]), 18)
        self.assertEqual(len(generated["SECRET_KEY"]), 64)
        self.assertIn(generated["ADMIN_PASSWORD"], output.getvalue())
        self.assertEqual(output.getvalue().count("Senha inicial:"), 1)

    def test_login_rejects_missing_csrf_and_invalid_password(self):
        page = self.client.get("/login")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Entre na sua conta", page.get_data(as_text=True))
        self.assertEqual(self.client.post("/login", data={
            "username": self.config.ADMIN_USERNAME,
            "password": self.config.ADMIN_PASSWORD,
        }).status_code, 400)

        token = self.csrf_token(page)
        response = self.client.post("/login", data={
            "csrf_token": token,
            "username": self.config.ADMIN_USERNAME,
            "password": "senha-incorreta",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Usuário ou senha inválidos", response.get_data(as_text=True))
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)

    def test_login_dashboard_and_logout(self):
        login_page = self.client.get("/login")
        response = self.client.post("/login", data={
            "csrf_token": self.csrf_token(login_page),
            "username": self.config.ADMIN_USERNAME,
            "password": self.config.ADMIN_PASSWORD,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        with self.client.session_transaction() as session:
            self.assertIn("user_id", session)

        dashboard = self.client.get("/")
        self.assertEqual(dashboard.status_code, 200)
        body = dashboard.get_data(as_text=True)
        self.assertIn("Painel de orçamentos", body)
        self.assertIn("Novo orçamento", body)

        self.assertEqual(self.client.post("/logout").status_code, 400)
        response = self.client.post("/logout", data={
            "csrf_token": self.csrf_token(dashboard),
        })
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_browser_opener_waits_for_server_then_opens_once(self):
        with patch("app.urllib.request.urlopen", return_value=nullcontext()) as request:
            with patch("app.webbrowser.open_new_tab") as open_browser:
                open_browser_when_ready("http://127.0.0.1:5000/login")
        request.assert_called_once_with("http://127.0.0.1:5000/login", timeout=0.5)
        open_browser.assert_called_once_with("http://127.0.0.1:5000/login")

    def test_run_local_respects_browser_setting_and_disables_debug(self):
        fake_app = SimpleNamespace(
            config={"APP_PORT": 5000, "AUTO_OPEN_BROWSER": False},
            run=Mock(),
        )
        with patch("app.create_app", return_value=fake_app):
            with patch("app.threading.Thread") as thread:
                run_local()
        thread.assert_not_called()
        fake_app.run.assert_called_once_with(
            host="127.0.0.1", port=5000, debug=False, use_reloader=False
        )

    def test_run_local_starts_one_browser_opener_when_enabled(self):
        fake_app = SimpleNamespace(
            config={"APP_PORT": 5000, "AUTO_OPEN_BROWSER": True},
            run=Mock(),
        )
        with patch("app.create_app", return_value=fake_app):
            with patch("app.threading.Thread") as thread:
                run_local()
        thread.assert_called_once_with(
            target=open_browser_when_ready,
            args=("http://127.0.0.1:5000/login",),
            name="crm-browser-opener",
            daemon=True,
        )
        thread.return_value.start.assert_called_once_with()

    def test_browser_opener_retries_until_login_responds(self):
        import urllib.error

        with patch("app.urllib.request.urlopen", side_effect=[
            urllib.error.URLError("not ready"), nullcontext()
        ]) as request:
            with patch("app.time.sleep"):
                with patch("app.webbrowser.open_new_tab") as open_browser:
                    open_browser_when_ready("http://127.0.0.1:5000/login")
        self.assertEqual(request.call_count, 2)
        open_browser.assert_called_once_with("http://127.0.0.1:5000/login")


if __name__ == "__main__":
    unittest.main()
