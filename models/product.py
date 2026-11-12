"""Consultas e persistência de produtos e serviços."""
from db import get_connection


def list_products(database_path: str, user_id: int):
    with get_connection(database_path) as connection:
        return connection.execute(
            "SELECT * FROM products WHERE user_id = ? ORDER BY name COLLATE NOCASE, id DESC",
            (user_id,),
        ).fetchall()


def get_product(database_path: str, user_id: int, product_id: int):
    with get_connection(database_path) as connection:
        return connection.execute(
            "SELECT * FROM products WHERE id = ? AND user_id = ?", (product_id, user_id)
        ).fetchone()


def create_product(database_path: str, user_id: int, values: dict) -> int:
    with get_connection(database_path) as connection:
        cursor = connection.execute(
            """INSERT INTO products (user_id, name, description, unit_price_cents)
               VALUES (:user_id, :name, :description, :unit_price_cents)""",
            {**values, "user_id": user_id},
        )
        return cursor.lastrowid


def update_product(database_path: str, user_id: int, product_id: int, values: dict) -> bool:
    with get_connection(database_path) as connection:
        cursor = connection.execute(
            """UPDATE products
               SET name = :name, description = :description,
                   unit_price_cents = :unit_price_cents,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = :id AND user_id = :user_id""",
            {**values, "id": product_id, "user_id": user_id},
        )
        return cursor.rowcount == 1


def delete_product(database_path: str, user_id: int, product_id: int) -> str:
    """Exclui somente produto sem item de orçamento vinculado."""
    with get_connection(database_path) as connection:
        exists = connection.execute(
            "SELECT 1 FROM products WHERE id = ? AND user_id = ?", (product_id, user_id)
        ).fetchone()
        if exists is None:
            return "missing"
        cursor = connection.execute(
            """DELETE FROM products
               WHERE id = ? AND user_id = ? AND NOT EXISTS (
                   SELECT 1 FROM quote_items WHERE product_id = ?
               )""",
            (product_id, user_id, product_id),
        )
        return "deleted" if cursor.rowcount == 1 else "linked"
