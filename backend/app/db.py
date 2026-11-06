from collections.abc import Generator

import psycopg
from psycopg.rows import dict_row

from app.config import settings


def get_conn() -> Generator[psycopg.Connection, None, None]:
    conn = psycopg.connect(settings.database_url, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()
