"""Aplicação local do CRM de Orçamentos e Propostas."""
from __future__ import annotations

import importlib.util
import secrets
import string
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from flask import Flask, g, session
from flask_wtf.csrf import CSRFProtect

from db import initialize_database
from models.user import get_user_by_id

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.py"
csrf = CSRFProtect()


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
COMPANY_NAME = "Mainhardt Soluções de Exemplo"
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
    print(f"Senha inicial: {admin_password}")
    print("Guarde a senha. Ela será preservada na configuração local.")


def load_config():
    ensure_local_config()
    spec = importlib.util.spec_from_file_location("local_config", CONFIG_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Não foi possível carregar config.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def create_app(test_config: dict | None = None) -> Flask:
    """Cria a aplicação, aplica o schema e configura a sessão e CSRF."""
    local_config = load_config()
    database_path = (BASE_DIR / local_config.DATABASE_PATH).resolve()

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=local_config.SECRET_KEY,
        DATABASE_PATH=str(database_path),
        WTF_CSRF_ENABLED=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,  # O servidor local usa HTTP em loopback.
        COMPANY_NAME=local_config.COMPANY_NAME,
        COMPANY_EMAIL=local_config.COMPANY_EMAIL,
        COMPANY_PHONE=local_config.COMPANY_PHONE,
        COMPANY_ADDRESS=local_config.COMPANY_ADDRESS,
        AUTO_OPEN_BROWSER=getattr(local_config, "AUTO_OPEN_BROWSER", True),
        APP_PORT=int(getattr(local_config, "APP_PORT", 5000)),
    )
    if test_config:
        app.config.update(test_config)

    initialize_database(
        app.config["DATABASE_PATH"],
        BASE_DIR / "schema.sql",
        local_config.ADMIN_USERNAME,
        local_config.ADMIN_PASSWORD,
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
    def load_logged_in_user() -> None:
        user_id = session.get("user_id")
        g.current_user = (
            get_user_by_id(app.config["DATABASE_PATH"], user_id)
            if user_id is not None
            else None
        )

    @app.context_processor
    def inject_template_values() -> dict:
        return {"current_user": g.get("current_user")}

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
