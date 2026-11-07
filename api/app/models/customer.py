from pydantic import BaseModel


class Customer(BaseModel):
    """A customer as returned by get_customer, joined with their service area."""

    id: int
    account_no: str
    full_name: str
    phone: str
    service_type: str
    status: str
    area_id: int
    area_name: str
    region: str
