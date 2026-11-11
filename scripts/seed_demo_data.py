"""Cria clientes, produtos e orçamentos de demonstração sem duplicá-los."""
from __future__ import annotations

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import create_app
from db import get_connection
from models.quote import create_quote


CLIENTS = [
    ("Demonstração - Ana Costa", "ana.costa@example.test", "(11) 98888-1001", "Costa Arquitetura", "Cliente demonstrativo para testar propostas."),
    ("Demonstração - Bruno Lima", "bruno.lima@example.test", "(21) 97777-2002", "Lima Consultoria", "Cliente demonstrativo para testar propostas."),
    ("Demonstração - Carla Mendes", "carla.mendes@example.test", "(31) 96666-3003", "Mendes Comércio", "Cliente demonstrativo para testar propostas."),
    ("Demonstração - Diego Rocha", "diego.rocha@example.test", "(41) 95555-4004", "Rocha Tecnologia", "Cliente demonstrativo para testar propostas."),
]

PRODUCTS = [
    ("Demonstração - Consultoria inicial", "Diagnóstico e plano de ação personalizado.", 45000),
    ("Demonstração - Implantação do sistema", "Configuração, implantação e treinamento da equipe.", 125000),
    ("Demonstração - Suporte mensal", "Atendimento técnico mensal, até 10 horas.", 38000),
    ("Demonstração - Identidade visual", "Criação de identidade visual e manual da marca.", 89000),
    ("Demonstração - Página institucional", "Design responsivo e publicação de página institucional.", 149000),
    ("Demonstração - Treinamento da equipe", "Workshop remoto de capacitação, com até 8 participantes.", 52000),
]


def ensure_client(connection, values):
    row = connection.execute("SELECT id FROM clients WHERE name = ?", (values[0],)).fetchone()
    if row:
        return row["id"]
    return connection.execute(
        "INSERT INTO clients (name, email, phone, company, notes) VALUES (?, ?, ?, ?, ?)",
        values,
    ).lastrowid


def ensure_product(connection, values):
    row = connection.execute("SELECT id FROM products WHERE name = ?", (values[0],)).fetchone()
    if row:
        return row["id"]
    return connection.execute(
        "INSERT INTO products (name, description, unit_price_cents) VALUES (?, ?, ?)",
        values,
    ).lastrowid


def main():
    app = create_app()
    database_path = app.config["DATABASE_PATH"]
    with get_connection(database_path) as connection:
        client_ids = [ensure_client(connection, row) for row in CLIENTS]
        product_ids = [ensure_product(connection, row) for row in PRODUCTS]

    quote_specs = [
        (0, "Consultoria e treinamento", [(0, 1), (5, 1)]),
        (1, "Implantação e suporte", [(1, 1), (2, 3)]),
        (2, "Identidade visual e página", [(3, 1), (4, 1)]),
        (3, "Consultoria e implantação", [(0, 2), (1, 1)]),
    ]
    created_quotes = 0
    for client_index, label, requested in quote_specs:
        note = f"Demonstração CRM: {label}. Registro fictício para validação do sistema."
        with get_connection(database_path) as connection:
            exists = connection.execute(
                "SELECT id FROM quotes WHERE client_id = ? AND notes = ?",
                (client_ids[client_index], note),
            ).fetchone()
        if exists:
            continue
        create_quote(
            database_path,
            client_ids[client_index],
            note,
            [{"product_id": product_ids[product_index], "quantity": quantity}
             for product_index, quantity in requested],
        )
        created_quotes += 1

    print(
        "Dados de demonstração prontos: "
        f"{len(CLIENTS)} clientes, {len(PRODUCTS)} produtos e "
        f"{created_quotes} novos orçamentos (existentes preservados)."
    )


if __name__ == "__main__":
    main()
