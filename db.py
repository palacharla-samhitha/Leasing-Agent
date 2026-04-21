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
    """Returns fully qualified table name."""
    return f"{CATALOG}.{SCHEMA}.{name}"


# ==============================================================================
# Backwards-compatible interface — keeps all routers working unchanged
# ==============================================================================

class DictCursor:
    """
    Mimics psycopg2 RealDictCursor interface.
    Converts %s params to ? for Databricks SQL.
    """
    def __init__(self, connection):
        self._conn   = connection
        self._cursor = connection.cursor()
        self.lastrowid = None

    def execute(self, query: str, params=None):
        # Convert PostgreSQL %s placeholders to Databricks ?
        databricks_query = query.replace("%s", "?")
        # Convert table names to fully qualified
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
    """Mimics psycopg2 connection interface."""

    def __init__(self):
        self._conn = sql.connect(
            server_hostname = DATABRICKS_HOST,
            http_path       = DATABRICKS_HTTP,
            access_token    = DATABRICKS_TOKEN,
        )

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        pass  # Delta Lake auto-commits

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def get_conn():
    """Drop-in replacement for psycopg2 get_conn()."""
    return DatabricksConnection()


def dict_cursor(conn):
    """Drop-in replacement for psycopg2 dict_cursor()."""
    return DictCursor(conn._conn)


# ==============================================================================
# Table name qualification
# ==============================================================================

# All table names used across routers
TABLES = [
    "inquiries", "properties", "units", "leases", "rent_charges",
    "documents", "lead_scores", "vacancy_plan", "pricing_rules",
    "ejari_registrations", "audit_events"
]

def _qualify_tables(query: str) -> str:
    """
    Replaces bare table names with fully qualified catalog.schema.table names.
    e.g. 'FROM inquiries' → 'FROM workspace.maf_gold.inquiries'
    """
    import re
    for t in TABLES:
        # Match table name as whole word, not already qualified
        pattern = rf'(?<![.\w])\b{t}\b(?!\s*\.)'
        replacement = f"{CATALOG}.{SCHEMA}.{t}"
        query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)
    return query