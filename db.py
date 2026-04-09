# ============================================================================
# db.py — PostgreSQL connection pool (psycopg2)
# COPY THIS FILE TO: project root (same level as app.py)
# AI Leasing Agent · MAF Properties · ReKnew · April 2026
#
# Single shared pool — all tool files import get_conn() from here.
# Credentials are read from .env — never hardcoded.
# ============================================================================

import os
from contextlib import contextmanager
from dotenv import load_dotenv
import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor

load_dotenv()

# ── Connection pool (1–10 connections, thread-safe) ──────────────────────────
_pool = pg_pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 5432)),
    dbname=os.getenv("DB_NAME", "leasing_agent"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", ""),
)


@contextmanager
def get_conn():
    """
    Context manager that checks out a connection from the pool,
    commits on success, rolls back on error, and always returns it.

    Usage:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM properties")
            rows = cur.fetchall()   # list of dicts — no column mapping needed
    """
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


# ── Convenience cursor ────────────────────────────────────────────────────────
def dict_cursor(conn):
    """
    Returns a RealDictCursor — rows come back as plain dicts automatically.
    Eliminates the need for manual col_names() / zip() conversions.

    Usage:
        with get_conn() as conn:
            cur = dict_cursor(conn)
            cur.execute("SELECT * FROM units WHERE unit_id = %s", (unit_id,))
            row = cur.fetchone()   # already a dict or None
    """
    return conn.cursor(cursor_factory=RealDictCursor)