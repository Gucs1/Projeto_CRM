"""Ponto de entrada do projeto. Esta fase prepara o banco local."""
from __future__ import annotations

import importlib.util
import secrets
import string
from pathlib import Path

from db import initialize_database

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.py"


def ensure_local_config() -> None:
    """Gera uma configuração privada e persistente no primeiro uso."""
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
'''
    CONFIG_PATH.write_text(local_config, encoding="utf-8")
    try:
        CONFIG_PATH.chmod(0o600)
    except OSError:
        pass


def load_config():
    ensure_local_config()
    spec = importlib.util.spec_from_file_location("local_config", CONFIG_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Não foi possível carregar config.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def initialize() -> tuple[Path, str, str]:
    config = load_config()
    database_path = (BASE_DIR / config.DATABASE_PATH).resolve()
    initialize_database(database_path, BASE_DIR / "schema.sql",
                        config.ADMIN_USERNAME, config.ADMIN_PASSWORD)
    return database_path, config.ADMIN_USERNAME, config.ADMIN_PASSWORD


if __name__ == "__main__":
    database_path, username, password = initialize()
    print("Banco CRM inicializado com sucesso.")
    print(f"Arquivo do banco: {database_path}")
    print(f"Usuário administrador: {username}")
    print(f"Senha inicial (salva em config.py): {password}")
    print("Na Fase 2, python app.py também iniciará a interface local.")
