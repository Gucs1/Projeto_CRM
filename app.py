"""Aplicação local do CRM de Orçamentos e Propostas."""
from __future__ import annotations

import importlib.util
import json
import logging
import os
import secrets
import string
import threading
import time
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
import urllib.error
import urllib.request
import webbrowser
from datetime import timedelta
from pathlib import Path

from flask import Flask, g, jsonify, render_template, request, session
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

from db import initialize_database
from models.user import get_user_by_id

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.py"
csrf = CSRFProtect()


class SafeJsonFormatter(logging.Formatter):
    """Emite eventos estruturados sem serializar headers ou dados do formulário."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "event": getattr(record, "event", record.getMessage()),
        }
        for field in ("request_id", "method", "route", "status", "duration_ms", "error_type"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class PrivacyAwareFlask(Flask):
    """Evita que Flask escreva mensagens arbitrárias de exceção nos logs."""

    def log_exception(self, exc_info) -> None:
        # A exceção será registrada pelo handler com rota e tipo, sem valores
        # submetidos em formulários que podem conter dados pessoais.
        return None


def ensure_local_config() -> None:
    """Gera configuração privada e persistente no primeiro uso."""
    if CONFIG_PATH.exists():
        return
    alphabet = string.ascii_letters + string.digits
    admin_password = "".join(secrets.choice(alphabet) for _ in range(18))
    local_config = f'''"""Configuração local privada, gerada automaticamente. Não compartilhe."""
SECRET_KEY = {secrets.token_urlsafe(48)!r}
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = {admin_password!r}
DATABASE_PATH = "instance/crm.sqlite3"
COMPANY_NAME = "Nexo CRM"
COMPANY_EMAIL = "contato@exemplo.local"
COMPANY_PHONE = "(11) 5555-0100"
COMPANY_ADDRESS = "Rua das Empresas, 100 - São Paulo, SP"
COMPANY_LOGO = "static/img/logo.png"
AUTO_OPEN_BROWSER = True
APP_PORT = 5000
'''
    CONFIG_PATH.write_text(local_config, encoding="utf-8")
    try:
        CONFIG_PATH.chmod(0o600)
    except OSError:
        pass
    print("Configuração inicial criada em config.py.")
    print("Usuário administrador: admin")
    print("Consulte a senha inicial no arquivo privado config.py.")


def load_config():
    load_dotenv(BASE_DIR / ".env", override=False)
    ensure_local_config()
    spec = importlib.util.spec_from_file_location("local_config", CONFIG_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Não foi possível carregar config.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().casefold() in {"1", "true", "yes", "on"}


def create_app(test_config: dict | None = None) -> Flask:
    """Cria a aplicação, aplica o schema e configura a sessão e CSRF."""
    local_config = load_config()
    database_value = os.getenv("DATABASE_PATH", local_config.DATABASE_PATH)
    database_path = (BASE_DIR / database_value).resolve()
    cookie_secure = env_bool("COOKIE_SECURE", False)

    app = PrivacyAwareFlask(__name__)
    app.logger.handlers.clear()
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(SafeJsonFormatter())
    app.logger.addHandler(log_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", local_config.SECRET_KEY),
        DATABASE_PATH=str(database_path),
        WTF_CSRF_ENABLED=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cookie_secure,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        SESSION_REFRESH_EACH_REQUEST=False,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        COMPANY_NAME=os.getenv("COMPANY_NAME", "Nexo CRM"),
        COMPANY_EMAIL=os.getenv("COMPANY_EMAIL", local_config.COMPANY_EMAIL),
        COMPANY_PHONE=os.getenv("COMPANY_PHONE", local_config.COMPANY_PHONE),
        COMPANY_ADDRESS=os.getenv("COMPANY_ADDRESS", local_config.COMPANY_ADDRESS),
        COMPANY_LOGO=str((BASE_DIR / os.getenv("COMPANY_LOGO", getattr(local_config, "COMPANY_LOGO", "static/img/logo.png"))).resolve()),
        AUTO_OPEN_BROWSER=env_bool("AUTO_OPEN_BROWSER", getattr(local_config, "AUTO_OPEN_BROWSER", True)),
        APP_PORT=int(os.getenv("APP_PORT", getattr(local_config, "APP_PORT", 5000))),
    )
    if test_config:
        app.config.update(test_config)
    if app.testing:
        app.logger.setLevel(logging.WARNING)

    initialize_database(
        app.config["DATABASE_PATH"],
        BASE_DIR / "schema.sql",
        os.getenv("ADMIN_USERNAME", local_config.ADMIN_USERNAME),
        os.getenv("ADMIN_PASSWORD", local_config.ADMIN_PASSWORD),
    )
    csrf.init_app(app)

    from controllers.auth import auth_bp
    from controllers.pages import pages_bp
    from controllers.clients import clients_bp
    from controllers.products import products_bp
    from controllers.quotes import quotes_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(quotes_bp)

    @app.before_request
    def begin_request_observation() -> None:
        g.request_id = secrets.token_hex(16)
        g.request_started_at = time.perf_counter()

    @app.before_request
    def load_logged_in_user() -> None:
        user_id = session.get("user_id")
        g.current_user = (
            get_user_by_id(
                app.config["DATABASE_PATH"], user_id, session.get("session_token")
            )
            if user_id is not None and session.get("session_token")
            else None
        )

    @app.context_processor
    def inject_template_values() -> dict:
        return {"current_user": g.get("current_user")}

    @app.get("/health")
    def health():
        """Verifica a disponibilidade local do processo e do SQLite sem expor dados."""
        try:
            with closing(sqlite3.connect(app.config["DATABASE_PATH"], timeout=1)) as connection:
                connection.execute("SELECT 1").fetchone()
        except sqlite3.Error:
            app.logger.warning(
                "Verificação local do banco falhou",
                extra={"event": "health_database_unavailable", "request_id": g.request_id},
            )
            return jsonify({"status": "unavailable"}), 503
        return jsonify({"status": "ok"}), 200

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Request-ID"] = g.get("request_id", secrets.token_hex(16))
        request_started_at = g.get("request_started_at")
        duration_ms = (
            round(max(0.0, time.perf_counter() - request_started_at) * 1000, 2)
            if request_started_at is not None else 0.0
        )
        app.logger.info(
            "Requisição concluída",
            extra={
                "event": "http_request",
                "request_id": response.headers["X-Request-ID"],
                "method": request.method,
                "route": request.url_rule.rule if request.url_rule else "unmatched",
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; font-src 'self'; "
            "style-src 'self'; script-src 'self'; object-src 'none'; "
            "base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
        )
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @app.errorhandler(500)
    def internal_server_error(error):
        original_error = getattr(error, "original_exception", None)
        app.logger.error(
            "Falha interna na requisição",
            extra={
                "event": "internal_error",
                "request_id": g.get("request_id"),
                "route": request.url_rule.rule if request.url_rule else "unmatched",
                "error_type": type(original_error or error).__name__,
            },
        )
        return render_template("errors/500.html"), 500

    @app.template_filter("brl")
    def format_brl(cents: int) -> str:
        value = int(cents)
        whole = f"{value // 100:,}".replace(",", ".")
        return f"R$ {whole},{value % 100:02d}"

    return app


def open_browser_when_ready(url: str, timeout: float = 15.0) -> None:
    """Abre a página uma vez, depois que o servidor local responde."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5):
                webbrowser.open_new_tab(url)
                return
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.2)


def run_local() -> None:
    app = create_app()
    port = app.config["APP_PORT"]
    url = f"http://127.0.0.1:{port}/login"
    if app.config["AUTO_OPEN_BROWSER"]:
        threading.Thread(
            target=open_browser_when_ready,
            args=(url,),
            name="crm-browser-opener",
            daemon=True,
        ).start()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    run_local()
