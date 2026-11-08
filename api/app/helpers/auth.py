"""Bearer-token auth for the API. Two callers, two tokens, each limited to its own routes:

  TOOLS_API_TOKEN      the agent        -> tool endpoints (lookup, outages, create ticket, SMS)
  DASHBOARD_API_TOKEN  the dashboard    -> dashboard endpoints (conversations, ticket queue, SMS outbox)
                       (Next.js server; staff sign in to the dashboard, the browser never sees it)

Callers send `Authorization: Bearer <token>`. If a token is not set, a random one is generated at
startup and a warning is logged. For TOOLS_API_TOKEN that still works when the agent runs in the
same process as the API (the default). DASHBOARD_API_TOKEN must be set, in both .env and
web/.env.local, for the dashboard to reach the API.
"""
import logging
import os
import secrets
from collections.abc import Callable

from fastapi import Header, HTTPException

log = logging.getLogger(__name__)


def _token(name: str, hint: str) -> str:
    value = os.environ.get(name) or ""
    if not value:
        value = secrets.token_urlsafe(32)
        log.warning("%s is not set; using a random per-process token. %s", name, hint)
    return value


TOOLS_API_TOKEN = _token("TOOLS_API_TOKEN",
                         "Set it in .env if the agent runs in a separate process or with multiple workers.")
DASHBOARD_API_TOKEN = _token("DASHBOARD_API_TOKEN",
                             "The dashboard can't reach the API until it is set in .env and web/.env.local.")


def _bearer(expected: str) -> Callable[..., None]:
    def check(authorization: str | None = Header(None, include_in_schema=False)) -> None:
        scheme, _, token = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not secrets.compare_digest(token.encode(), expected.encode()):
            raise HTTPException(401, "Missing or invalid token.", headers={"WWW-Authenticate": "Bearer"})
    return check


require_service_token = _bearer(TOOLS_API_TOKEN)
require_dashboard_token = _bearer(DASHBOARD_API_TOKEN)


def service_headers() -> dict[str, str]:
    """Headers the agent sends with every tool call."""
    return {"Authorization": f"Bearer {TOOLS_API_TOKEN}"}


def dashboard_headers() -> dict[str, str]:
    """Headers the dashboard sends (used by tests; the Next.js server sets its own)."""
    return {"Authorization": f"Bearer {DASHBOARD_API_TOKEN}"}
