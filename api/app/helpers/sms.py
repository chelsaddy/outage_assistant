"""Send SMS through Twilio, or simulate it when Twilio isn't configured.

Settings (read on every call, so tests and .env changes take effect without a restart):
  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER  - all three set => real SMS
  SMS_REDIRECT_TO  - optional; send every real SMS here instead (Twilio trial accounts
                     can only text verified numbers, and the seeded customers are fake)
"""
import os
from dataclasses import dataclass

import httpx

TWILIO_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


@dataclass
class SmsResult:
    status: str                # 'sent' | 'failed' | 'simulated'
    sent_to: str               # the number actually texted (differs when redirected)
    provider_sid: str | None = None
    error: str | None = None


def twilio_configured() -> bool:
    return all(os.environ.get(k) for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"))


def _twilio_post(to: str, body: str) -> httpx.Response:
    sid = os.environ["TWILIO_ACCOUNT_SID"]
    return httpx.post(
        TWILIO_URL.format(sid=sid),
        auth=(sid, os.environ["TWILIO_AUTH_TOKEN"]),
        data={"To": to, "From": os.environ["TWILIO_FROM_NUMBER"], "Body": body},
        timeout=10,
    )


def send_sms_message(to: str, body: str) -> SmsResult:
    if not twilio_configured():
        return SmsResult(status="simulated", sent_to=to)

    target = os.environ.get("SMS_REDIRECT_TO") or to
    try:
        r = _twilio_post(target, body)
    except httpx.HTTPError as exc:
        return SmsResult(status="failed", sent_to=target, error=f"Could not reach Twilio: {exc}")

    data = r.json() if r.content else {}
    if r.status_code >= 400:
        return SmsResult(status="failed", sent_to=target, error=data.get("message", f"Twilio HTTP {r.status_code}"))
    return SmsResult(status="sent", sent_to=target, provider_sid=data.get("sid"))
