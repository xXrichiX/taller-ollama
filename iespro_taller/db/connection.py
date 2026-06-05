from contextlib import contextmanager
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from config import (
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
)


def get_connection(database: str | None = "__default__"):
    kwargs = {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": False,
    }
    if database == "__default__":
        kwargs["database"] = MYSQL_DATABASE
    elif database is not None:
        kwargs["database"] = database
    return pymysql.connect(**kwargs)


@contextmanager
def db_cursor(database: str | None = "__default__"):
    conn = get_connection(database)
    try:
        with conn.cursor() as cursor:
            yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(query: str, params: tuple | list | None = None) -> list[dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute(query, params or ())
        return list(cur.fetchall())


def fetch_one(query: str, params: tuple | list | None = None) -> dict[str, Any] | None:
    with db_cursor() as cur:
        cur.execute(query, params or ())
        return cur.fetchone()


def execute(query: str, params: tuple | list | None = None) -> int:
    with db_cursor() as cur:
        cur.execute(query, params or ())
        return cur.lastrowid or 0


def execute_script_file(path: str, database: str | None = None) -> None:
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()

    conn = get_connection(database)
    try:
        with conn.cursor() as cur:
            for statement in _split_statements(sql):
                if statement.strip():
                    cur.execute(statement)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _split_statements(sql: str) -> list[str]:
    statements = []
    current = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(current))
            current = []
    if current:
        statements.append("\n".join(current))
    return statements


def test_connection() -> tuple[bool, str]:
    try:
        row = fetch_one(
            "SELECT DATABASE() AS db, COUNT(*) AS tablas "
            "FROM information_schema.tables WHERE table_schema = %s",
            (MYSQL_DATABASE,),
        )
        if row is None:
            return False, "No se pudo conectar a MySQL."
        return True, f"Conectado a `{MYSQL_DATABASE}` ({row['tablas']} tablas)."
    except Exception as exc:
        return False, str(exc)
