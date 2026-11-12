"""Persistência de orçamentos e consultas do painel comercial."""
from db import get_connection

MAX_SQLITE_INTEGER = 9_223_372_036_854_775_807
MAX_QUOTE_ITEMS = 50
MAX_ITEM_QUANTITY = 1_000_000
QUOTE_STATUSES = ("Enviado", "Aprovado", "Recusado")
QUOTE_PRIORITIES = ("Baixa", "Média", "Alta")
DEFAULT_QUOTE_PRIORITY = "Média"


def create_quote(database_path: str, client_id: int, notes: str,
                 requested_items: list[dict],
                 priority: str = DEFAULT_QUOTE_PRIORITY) -> int:
    """Cria orçamento e itens em uma transação usando os preços do catálogo."""
    if priority not in QUOTE_PRIORITIES:
        raise ValueError("Selecione uma prioridade válida.")
    if not requested_items:
        raise ValueError("Adicione pelo menos um produto ou serviço.")
    if len(requested_items) > MAX_QUOTE_ITEMS:
        raise ValueError(f"O orçamento pode conter até {MAX_QUOTE_ITEMS} itens.")

    with get_connection(database_path) as connection:
        client = connection.execute(
            """SELECT id, name, email, phone, company
               FROM clients WHERE id = ?""",
            (client_id,),
        ).fetchone()
        if client is None:
            raise ValueError("Selecione um cliente válido.")

        items = []
        total_cents = 0
        for requested in requested_items:
            product = connection.execute(
                """SELECT id, name, description, unit_price_cents
                   FROM products WHERE id = ?""",
                (requested["product_id"],),
            ).fetchone()
            if product is None:
                raise ValueError("Um dos produtos selecionados não está mais disponível.")

            quantity = requested["quantity"]
            if not isinstance(quantity, int) or not 1 <= quantity <= MAX_ITEM_QUANTITY:
                raise ValueError("Cada quantidade deve ser um número inteiro positivo.")

            unit_price_cents = product["unit_price_cents"]
            line_total_cents = unit_price_cents * quantity
            if line_total_cents > MAX_SQLITE_INTEGER:
                raise ValueError("O subtotal de um item ultrapassa o limite aceito pelo sistema.")
            total_cents += line_total_cents
            if total_cents > MAX_SQLITE_INTEGER:
                raise ValueError("O total ultrapassa o limite aceito pelo sistema.")
            items.append({
                "product_id": product["id"],
                "product_name": product["name"],
                "description": product["description"],
                "quantity": quantity,
                "unit_price_cents": unit_price_cents,
                "line_total_cents": line_total_cents,
            })

        cursor = connection.execute(
            """INSERT INTO quotes
               (client_id, client_name, client_email, client_phone, client_company,
                status, priority, notes, total_cents)
               VALUES (?, ?, ?, ?, ?, 'Enviado', ?, ?, ?)""",
            (client["id"], client["name"], client["email"], client["phone"],
             client["company"], priority, notes, total_cents),
        )
        quote_id = cursor.lastrowid
        connection.executemany(
            """INSERT INTO quote_items
               (quote_id, product_id, product_name, description, quantity,
                unit_price_cents, line_total_cents)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [(
                quote_id, item["product_id"], item["product_name"],
                item["description"], item["quantity"],
                item["unit_price_cents"], item["line_total_cents"],
            ) for item in items],
        )
        return quote_id


def get_dashboard_data(database_path: str, recent_limit: int = 6) -> dict:
    with get_connection(database_path) as connection:
        counts = connection.execute(
            """SELECT COUNT(*) AS total,
                      COALESCE(SUM(CASE WHEN status = 'Aprovado' THEN 1 ELSE 0 END), 0) AS approved,
                      COALESCE(SUM(CASE WHEN status = 'Recusado' THEN 1 ELSE 0 END), 0) AS declined
               FROM quotes"""
        ).fetchone()
        recent = connection.execute(
            """SELECT id, client_name, status, priority, total_cents, created_at
               FROM quotes ORDER BY created_at DESC, id DESC LIMIT ?""",
            (recent_limit,),
        ).fetchall()
        return {"counts": dict(counts), "recent": recent}


def list_quotes(database_path: str):
    with get_connection(database_path) as connection:
        return connection.execute(
            """SELECT id, client_id, client_name, status, priority, total_cents, created_at
               FROM quotes ORDER BY created_at DESC, id DESC"""
        ).fetchall()


def get_quote(database_path: str, quote_id: int):
    with get_connection(database_path) as connection:
        quote = connection.execute(
            "SELECT * FROM quotes WHERE id = ?", (quote_id,)
        ).fetchone()
        if quote is None:
            return None
        items = connection.execute(
            "SELECT * FROM quote_items WHERE quote_id = ? ORDER BY id",
            (quote_id,),
        ).fetchall()
        return {"quote": quote, "items": items}


def list_client_quotes(database_path: str, client_id: int):
    with get_connection(database_path) as connection:
        client = connection.execute(
            "SELECT id, name, email, phone, company FROM clients WHERE id = ?",
            (client_id,),
        ).fetchone()
        if client is None:
            return None
        quotes = connection.execute(
            """SELECT id, client_id, client_name, status, priority, total_cents, created_at
               FROM quotes WHERE client_id = ?
               ORDER BY created_at DESC, id DESC""",
            (client_id,),
        ).fetchall()
        return {"client": client, "quotes": quotes}


def update_quote_status(database_path: str, quote_id: int, status: str) -> bool:
    if status not in QUOTE_STATUSES:
        return False
    with get_connection(database_path) as connection:
        cursor = connection.execute(
            """UPDATE quotes SET status = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (status, quote_id),
        )
        return cursor.rowcount == 1


def update_quote_priority(database_path: str, quote_id: int, priority: str) -> bool:
    """Atualiza prioridade somente para valores permitidos."""
    if priority not in QUOTE_PRIORITIES:
        return False
    with get_connection(database_path) as connection:
        cursor = connection.execute(
            """UPDATE quotes SET priority = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (priority, quote_id),
        )
        return cursor.rowcount == 1
