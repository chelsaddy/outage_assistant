from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ServiceType = Literal["fibre", "dsl", "mobile", "fixed_wireless"]


class Outage(BaseModel):
    """One active outage, with the restore estimate pre-computed for the agent."""

    id: int
    service_type: str
    cause: str
    started_at: datetime
    eta: datetime | None
    minutes_until_eta: int | None  # negative once the ETA has passed
    eta_overdue: bool


class OutageCheck(BaseModel):
    """Result of check_outages: says plainly whether a known outage covers the area."""

    area_id: int
    area_name: str
    service_type: ServiceType | None
    has_active_outage: bool
    outages: list[Outage]
