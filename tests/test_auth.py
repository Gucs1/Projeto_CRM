"""Valida login, proteção de rotas, CSRF e abertura local do navegador."""
import re
import io
import json
import logging
import os
import tempfile
import unittest
from contextlib import nullcontext, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import runpy

import app as crm_app
from app import SafeJsonFormatter, create_app, load_config, open_browser_when_ready, run_local
from db import get_connection
from models.user import create_user


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

    def test_health_reports_only_process_and_database_availability(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})
        self.assertNotIn(self.app.config["DATABASE_PATH"], response.get_data(as_text=True))
        self.assertRegex(response.headers["X-Request-ID"], r"^[a-f0-9]{32}$")

    def test_safe_json_formatter_includes_only_allowlisted_observation_fields(self):
        record = logging.LogRecord("app", logging.INFO, __file__, 1, "private payload", (), None)
        record.event = "http_request"
        record.request_id = "a" * 32
        record.method = "GET"
        record.route = "/quotes/<int:quote_id>"
        record.status = 200
        record.duration_ms = 12.5
        rendered = SafeJsonFormatter().format(record)
        event = json.loads(rendered)
        self.assertEqual(event["event"], "http_request")
        self.assertEqual(event["request_id"], "a" * 32)
        self.assertEqual(event["route"], "/quotes/<int:quote_id>")
        self.assertNotIn("private payload", rendered)
        self.assertNotIn("pathname", event)

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
        self.assertNotIn(generated["ADMIN_PASSWORD"], output.getvalue())
        self.assertNotIn("Senha inicial:", output.getvalue())
        self.assertIn("config.py", output.getvalue())

    def test_login_rejects_missing_csrf_and_invalid_password(self):
        page = self.client.get("/login")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Bem-vindo de volta", page.get_data(as_text=True))
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

    def test_login_page_has_animated_sign_in_and_registration_panels(self):
        response = self.client.get("/login")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('data-auth-panel="login"', body)
        self.assertIn('data-auth-panel="register"', body)
        self.assertIn('data-auth-switch="register"', body)
        self.assertIn("Nexo CRM", body)
        self.assertIn("auth-track", body)
        self.assertIn("register", self.client.get("/register").get_data(as_text=True))

    def test_registration_requires_csrf_terms_valid_email_and_strong_matching_password(self):
        page = self.client.get("/register")
        self.assertEqual(self.client.post("/register", data={
            "email": "person@example.com", "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!", "terms_accepted": "on",
        }).status_code, 400)

        cases = [
            ({"email": "invalid", "password": "StrongPassword123!", "confirm_password": "StrongPassword123!", "terms_accepted": "on"}, "e-mail válido"),
            ({"email": "person@example.com", "password": "short", "confirm_password": "short", "terms_accepted": "on"}, "12 e 128"),
            ({"email": "person@example.com", "password": "StrongPassword123!", "confirm_password": "DifferentPassword123!", "terms_accepted": "on"}, "não conferem"),
            ({"email": "person@example.com", "password": "StrongPassword123!", "confirm_password": "StrongPassword123!"}, "Aceite os termos"),
        ]
        for values, message in cases:
            with self.subTest(message=message):
                token_page = self.client.get("/register")
                response = self.client.post("/register", data={
                    **values, "csrf_token": self.csrf_token(token_page),
                }, follow_redirects=True)
                self.assertIn(message, response.get_data(as_text=True))

        with get_connection(self.app.config["DATABASE_PATH"]) as connection:
            self.assertEqual(connection.execute(
                "SELECT COUNT(*) FROM users WHERE username = 'person@example.com'"
            ).fetchone()[0], 0)

    def test_registration_normalizes_email_hashes_password_and_creates_isolated_session(self):
        page = self.client.get("/register")
        response = self.client.post("/register", data={
            "csrf_token": self.csrf_token(page),
            "email": "  Person@Example.com ",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
            "terms_accepted": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        with get_connection(self.app.config["DATABASE_PATH"]) as connection:
            user = connection.execute(
                "SELECT * FROM users WHERE username = 'person@example.com'"
            ).fetchone()
            self.assertIsNotNone(user)
            self.assertNotEqual(user["password_hash"], "StrongPassword123!")
            self.assertIsNotNone(user["terms_accepted_at"])
            self.assertEqual(user["terms_version"], "2026-11-12")
        with self.client.session_transaction() as session:
            self.assertEqual(session["user_id"], user["id"])
            self.assertTrue(session.permanent)

        self.client.post("/logout", data={"csrf_token": self.csrf_token(self.client.get("/"))})
        login_page = self.client.get("/login")
        login = self.client.post("/login", data={
            "csrf_token": self.csrf_token(login_page),
            "username": "PERSON@example.com", "password": "StrongPassword123!",
        })
        self.assertEqual(login.status_code, 302)

    def test_duplicate_registration_is_case_insensitive_and_does_not_reveal_password_data(self):
        create_user(
            self.app.config["DATABASE_PATH"], "person@example.com",
            "StrongPassword123!", "test-version",
        )
        page = self.client.get("/register")
        response = self.client.post("/register", data={
            "csrf_token": self.csrf_token(page), "email": "PERSON@example.com",
            "password": "AnotherPassword123!", "confirm_password": "AnotherPassword123!",
            "terms_accepted": "on",
        }, follow_redirects=True)
        self.assertIn("Não foi possível criar a conta", response.get_data(as_text=True))

    def test_security_response_headers_are_present(self):
        response = self.client.get("/login")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
        self.assertNotIn("unsafe-inline", response.headers["Content-Security-Policy"])
        self.assertNotIn("cdn.tailwindcss.com", response.get_data(as_text=True))
        css = self.client.get("/static/css/tailwind.css")
        self.assertEqual(css.status_code, 200)
        self.assertIn(".bg-brand-600", css.get_data(as_text=True))
        css.close()

    def test_environment_configuration_can_enable_https_cookie_policy(self):
        env_db = str(Path(self.temp_dir.name) / "environment.sqlite3")
        with patch.dict(os.environ, {
            "SECRET_KEY": "environment-only-test-key",
            "COMPANY_NAME": "Nexo CRM QA",
            "DATABASE_PATH": env_db,
            "COOKIE_SECURE": "true",
            "APP_PORT": "5111",
        }):
            configured_app = create_app({"AUTO_OPEN_BROWSER": False})
            self.assertEqual(configured_app.config["SECRET_KEY"], "environment-only-test-key")
            self.assertTrue(configured_app.config["SESSION_COOKIE_SECURE"])
            self.assertEqual(configured_app.config["APP_PORT"], 5111)
            self.assertEqual(configured_app.config["COMPANY_NAME"], "Nexo CRM QA")
            response = configured_app.test_client().get("/login")
            self.assertIn("max-age=31536000", response.headers["Strict-Transport-Security"])

    def test_repeated_login_failures_are_rate_limited(self):
        for attempt in range(5):
            page = self.client.get("/login")
            response = self.client.post("/login", data={
                "csrf_token": self.csrf_token(page),
                "username": self.config.ADMIN_USERNAME,
                "password": "wrong-password",
            })
            expected_status = 429 if attempt == 4 else 200
            self.assertEqual(response.status_code, expected_status)
        self.assertIn("Aguarde 15 minutos", response.get_data(as_text=True))

        page = self.client.get("/login")
        blocked_valid_login = self.client.post("/login", data={
            "csrf_token": self.csrf_token(page),
            "username": self.config.ADMIN_USERNAME,
            "password": self.config.ADMIN_PASSWORD,
        })
        self.assertEqual(blocked_valid_login.status_code, 429)

    def test_a_new_login_and_logout_revoke_previous_session_tokens(self):
        self.assertEqual(self.client.post("/login", data={
            "csrf_token": self.csrf_token(self.client.get("/login")),
            "username": self.config.ADMIN_USERNAME,
            "password": self.config.ADMIN_PASSWORD,
        }).status_code, 302)
        with self.client.session_transaction() as session:
            old_user_id = session["user_id"]
            first_token = session["session_token"]

        second_client = self.app.test_client()
        page = second_client.get("/login")
        self.assertEqual(second_client.post("/login", data={
            "csrf_token": self.csrf_token(page),
            "username": self.config.ADMIN_USERNAME,
            "password": self.config.ADMIN_PASSWORD,
        }).status_code, 302)
        with second_client.session_transaction() as session:
            second_token = session["session_token"]
        self.assertNotEqual(first_token, second_token)
        self.assertEqual(self.client.get("/").headers["Location"], "/login")

        dashboard = second_client.get("/")
        second_client.post("/logout", data={"csrf_token": self.csrf_token(dashboard)})
        with second_client.session_transaction() as session:
            session["user_id"] = old_user_id
            session["session_token"] = second_token
        self.assertEqual(second_client.get("/").headers["Location"], "/login")

    def test_unhandled_error_is_logged_without_exception_details_to_visitor_or_logs(self):
        self.app.config["PROPAGATE_EXCEPTIONS"] = False

        @self.app.get("/test-private-error")
        def private_error():
            raise ValueError("private@example.com was not supposed to be logged")

        with self.assertLogs("app", level="ERROR") as captured:
            response = self.client.get("/test-private-error")
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private@example.com", response.get_data(as_text=True))
        error_record = next(record for record in captured.records if record.levelname == "ERROR")
        self.assertEqual(error_record.event, "internal_error")
        self.assertEqual(error_record.error_type, "ValueError")
        self.assertEqual(error_record.request_id, response.headers["X-Request-ID"])
        self.assertNotIn("private@example.com", " ".join(captured.output))

    def test_browser_opener_waits_for_server_then_opens_once(self):
        with patch("app.urllib.request.urlopen", return_value=nullcontext()) as request:
            with patch("app.webbrowser.open_new_tab") as open_browser:
                open_browser_when_ready("http://127.0.0.1:5000/login")
        request.assert_called_once_with("http://127.0.0.1:5000/login", timeout=0.5)
        open_browser.assert_called_once_with("http://127.0.0.1:5000/login")

    def test_browser_opener_rejects_non_loopback_urls(self):
        with patch("app.urllib.request.urlopen") as request:
            with patch("app.webbrowser.open_new_tab") as open_browser:
                open_browser_when_ready("https://example.com")
                open_browser_when_ready("http://user@127.0.0.1:5000/login")
        request.assert_not_called()
        open_browser.assert_not_called()

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
