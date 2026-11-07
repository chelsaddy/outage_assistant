import os

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://outage:outage@localhost:5432/outage")


def db():
    """Open a Postgres connection whose rows come back as dicts."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)
