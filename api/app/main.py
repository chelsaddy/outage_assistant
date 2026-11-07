"""Tools API for the Telecom Outage Assistant.

The agent calls these endpoints as tools:
  GET  /customers/lookup   -> get_customer
  GET  /outages?area_id=   -> check_outages   (next)
  POST /tickets            -> create_ticket   (next)
  POST /sms                -> send_sms        (next)
"""
from fastapi import FastAPI, HTTPException, Query

from app.helpers import db, normalize_phone
from app.models import Customer

app = FastAPI(title="Telecom Outage Assistant: Tools API")


@app.get("/health")
def health():
    with db() as conn:
        customers = conn.execute("SELECT count(*) AS n FROM customers").fetchone()["n"]
        active = conn.execute("SELECT count(*) AS n FROM outages WHERE status = 'active'").fetchone()["n"]
    return {"status": "ok", "customers": customers, "active_outages": active}


@app.get("/customers/lookup", response_model=Customer)
def get_customer(
    phone: str | None = Query(None, description="Customer phone number, any common format"),
    account_no: str | None = Query(None, description="Account number, e.g. ACC-100001"),
):
    """Find one customer by phone number or account number."""
    if bool(phone) == bool(account_no):
        raise HTTPException(422, "Provide exactly one of 'phone' or 'account_no'.")

    if phone:
        where, value = "c.phone = %s", normalize_phone(phone)
    else:
        where, value = "c.account_no = %s", account_no.strip().upper()

    with db() as conn:
        row = conn.execute(
            f"""
            SELECT c.id, c.account_no, c.full_name, c.phone, c.service_type, c.status,
                   c.area_id, a.name AS area_name, a.region
            FROM customers c JOIN service_areas a ON a.id = c.area_id
            WHERE {where}
            """,
            (value,),
        ).fetchone()

    if row is None:
        raise HTTPException(404, "No customer found with those details.")
    return row
