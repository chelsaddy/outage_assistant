"""Service-token auth for the tool endpoints.

The tool endpoints (customer lookup, outages, ticket creation, SMS) are for the agent only.
Callers must send `Authorization: Bearer <TOOLS_API_TOKEN>`.

If TOOLS_API_TOKEN is not set, a random token is generated at startup. That works when the agent
and the API run in the same process (the default), but set it explicitly when running more than
one worker or running the agent separately.
"""
import logging
import os
import secrets

from fastapi import Header, HTTPException

log = logging.getLogger(__name__)

TOOLS_API_TOKEN = os.environ.get("TOOLS_API_TOKEN") or ""
if not TOOLS_API_TOKEN:
    TOOLS_API_TOKEN = secrets.token_urlsafe(32)
    log.warning("TOOLS_API_TOKEN is not set; using a random per-process token. "
                "Set it in .env if the agent runs in a separate process or with multiple workers.")


def service_headers() -> dict[str, str]:
    """Headers the agent sends with every tool call."""
    return {"Authorization": f"Bearer {TOOLS_API_TOKEN}"}


def require_service_token(authorization: str | None = Header(None, include_in_schema=False)) -> None:
    """FastAPI dependency: reject requests without the service token."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(token.encode(), TOOLS_API_TOKEN.encode()):
        raise HTTPException(401, "Missing or invalid service token.", headers={"WWW-Authenticate": "Bearer"})
