import os

import psycopg
from psycopg.rows import dict_row

# No built-in default: credentials come from the environment (.env), never from the code.
DATABASE_URL = os.environ.get("DATABASE_URL", "")


def db():
    """Open a Postgres connection whose rows come back as dicts."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set. Add it to .env (see .env.example) "
                           "and start the API with --env-file ../.env.")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)
