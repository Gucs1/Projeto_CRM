"""Consultas e persistência de clientes."""
from db import get_connection


def list_clients(database_path: str, search: str = ""):
    with get_connection(database_path) as connection:
        if search:
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            return connection.execute(
                "SELECT * FROM clients WHERE name LIKE ? ESCAPE '\\' "
                "ORDER BY name COLLATE NOCASE, id DESC",
                (f"%{escaped}%",),
            ).fetchall()
        return connection.execute(
            "SELECT * FROM clients ORDER BY name COLLATE NOCASE, id DESC"
        ).fetchall()


def get_client(database_path: str, client_id: int):
    with get_connection(database_path) as connection:
        return connection.execute(
            "SELECT * FROM clients WHERE id = ?", (client_id,)
        ).fetchone()


def create_client(database_path: str, values: dict) -> int:
    with get_connection(database_path) as connection:
        cursor = connection.execute(
            """INSERT INTO clients (name, email, phone, company, notes)
               VALUES (:name, :email, :phone, :company, :notes)""",
            values,
        )
        return cursor.lastrowid


def update_client(database_path: str, client_id: int, values: dict) -> bool:
    with get_connection(database_path) as connection:
        cursor = connection.execute(
            """UPDATE clients
               SET name = :name, email = :email, phone = :phone,
                   company = :company, notes = :notes,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = :id""",
            {**values, "id": client_id},
        )
        return cursor.rowcount == 1


def delete_client(database_path: str, client_id: int) -> str:
    """Exclui apenas cliente sem orçamento vinculado."""
    with get_connection(database_path) as connection:
        exists = connection.execute(
            "SELECT 1 FROM clients WHERE id = ?", (client_id,)
        ).fetchone()
        if exists is None:
            return "missing"
        cursor = connection.execute(
            """DELETE FROM clients
               WHERE id = ? AND NOT EXISTS (
                   SELECT 1 FROM quotes WHERE client_id = ?
               )""",
            (client_id, client_id),
        )
        return "deleted" if cursor.rowcount == 1 else "linked"
