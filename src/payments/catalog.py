"""
HC-XCDSS Service & Consultation Catalog
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel


class ServiceDefinition(BaseModel):
    service_id: str
    name: str
    description: str
    amount_minor: int  # in minor units, e.g. paise (49900 = ₹499.00)
    currency: str = "INR"
    active: bool = True
    platform_fee_percent: float = 20.0  # Configurable platform commission


# --------------------------------------------------
# Canonical Service Catalog (Source of Truth)
# --------------------------------------------------

SERVICE_CATALOG: Dict[str, ServiceDefinition] = {
    "XRAY_PROFESSIONAL_REVIEW": ServiceDefinition(
        service_id="XRAY_PROFESSIONAL_REVIEW",
        name="Professional Chest X-Ray Review",
        description="Independent comprehensive radiological review and clinical report validation by a verified physician specialist.",
        amount_minor=49900,  # ₹499.00
        currency="INR",
        active=True,
        platform_fee_percent=20.0,
    )
}


def get_service_or_raise(service_id: str) -> ServiceDefinition:
    """
    Lookup service definition by ID. Raises ValueError if not found or inactive.
    """
    service = SERVICE_CATALOG.get(service_id)
    if not service or not service.active:
        raise ValueError(f"Invalid or unavailable service ID: '{service_id}'.")
    return service
