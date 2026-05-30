"""DataCal — research data volume calculation core (Phase 1, Plan).

Public API:
    from datacal import Campaign, Instrument, Leg, Deployment, calculate
    from datacal import campaign_from_dict, to_madmp
"""

from __future__ import annotations

from .engine import Bucket, CampaignResult, calculate
from .madmp import to_madmp
from .models import (
    Campaign,
    Deployment,
    Instrument,
    Leg,
    campaign_from_dict,
)

__version__ = "0.1.0"

__all__ = [
    "Campaign",
    "Instrument",
    "Leg",
    "Deployment",
    "campaign_from_dict",
    "calculate",
    "CampaignResult",
    "Bucket",
    "to_madmp",
    "__version__",
]
