# ==============================================================================
# db.py — Databricks SQL connection (backwards compatible with psycopg2 interface)
# MAF AI Leasing Agent · ReKnew · April 2026
# ==============================================================================

from databricks import sql
import os
from dotenv import load_dotenv

load_dotenv()

DATABRICKS_HOST  = os.getenv("DATABRICKS_HOST", "")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "")
DATABRICKS_HTTP  = os.getenv("DATABRICKS_HTTP_PATH", "")
CATALOG          = os.getenv("DATABRICKS_CATALOG", "workspace")
SCHEMA           = os.getenv("DATABRICKS_SCHEMA", "maf_gold")


def table(name: str) -> str:
    return f"{CATALOG}.{SCHEMA}.{name}"


TABLES = [
    "inquiries", "properties", "units", "leases", "rent_charges",
    "documents", "lead_scores", "vacancy_plan", "pricing_rules",
    "ejari_registrations", "audit_events"
]


def _qualify_tables(query: str) -> str:
    import re
    for t in TABLES:
        pattern = rf'(?<![.\w])\b{t}\b(?!\s*\.)'
        replacement = f"{CATALOG}.{SCHEMA}.{t}"
        query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
    return query


class DictCursor:
    def __init__(self, connection):
        self._conn   = connection
        self._cursor = connection.cursor()

    def execute(self, query: str, params=None):
        databricks_query = query.replace("%s", "?")
        databricks_query = _qualify_tables(databricks_query)
        self._cursor.execute(databricks_query, list(params) if params else [])

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in self._cursor.description]
        return dict(zip(cols, row))

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self._cursor.description]
        return [dict(zip(cols, row)) for row in rows]

    def close(self):
        self._cursor.close()


class DatabricksConnection:
    def __init__(self):
        self._conn = sql.connect(
            server_hostname = DATABRICKS_HOST,
            http_path       = DATABRICKS_HTTP,
            access_token    = DATABRICKS_TOKEN,
        )

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        pass

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def get_conn():
    return DatabricksConnection()


def dict_cursor(conn):
    return DictCursor(conn._conn)