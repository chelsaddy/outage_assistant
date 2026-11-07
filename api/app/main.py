"""Tools API for the Telecom Outage Assistant.

Saturday adds the four agent tools here:
  GET  /customers/lookup   -> get_customer
  GET  /outages?area_id=   -> check_outages
  POST /tickets            -> create_ticket
  POST /sms                -> send_sms
"""
import os

import psycopg
from fastapi import FastAPI

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://outage:outage@localhost:5432/outage")

app = FastAPI(title="Telecom Outage Assistant: Tools API")


def db():
    return psycopg.connect(DATABASE_URL)


@app.get("/health")
def health():
    with db() as conn:
        customers = conn.execute("SELECT count(*) FROM customers").fetchone()[0]
        active = conn.execute("SELECT count(*) FROM outages WHERE status = 'active'").fetchone()[0]
    return {"status": "ok", "customers": customers, "active_outages": active}
