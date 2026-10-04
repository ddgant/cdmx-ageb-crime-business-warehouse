"""Database access helpers shared by the ETL scripts and the notebooks."""
from __future__ import annotations

import os

import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

import config  # noqa: F401  (loads the .env file as a side effect)


def get_engine() -> Engine:
    """SQLAlchemy engine built from the PG* environment variables (see .env.example)."""
    return create_engine(config.db_url())


def get_connection():
    """Plain psycopg2 connection, used to run multi-statement SQL scripts."""
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE", "cdmx_dw"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", "postgres"),
    )
