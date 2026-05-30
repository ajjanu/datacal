"""Minimal maDMP export (RDA DMP Common Standard v1.1).

This is the interoperability hook: it emits a `{"dmp": {...}}` structure shaped
to the RDA DMP Common Standard so DataCal output can be ingested by RDMO,
DMPTool, Argos and other tools that consume maDMP JSON.

SCOPE / HONESTY: this is a MINIMAL, schema-SHAPED export, not a certified-valid
maDMP. It populates the fields DataCal actually owns (dataset volumes via
distribution.byte_size, one dataset per research group). Fields that require
human/institutional input are emitted as explicit TODO placeholders rather than
invented. Validate against the official schema before submitting to a funder:
https://github.com/RDA-DMP-Common/RDA-DMP-Common-Standard
"""

from __future__ import annotations

from datetime import date

from .engine import CampaignResult


def to_madmp(result: CampaignResult, *, language: str = "eng") -> dict:
    """Map a CampaignResult to a minimal RDA Common Standard maDMP dict.

    One `dataset` is emitted per research group, with a single `distribution`
    carrying the calculated `byte_size` (integer bytes, per the standard).
    """
    today = date.today().isoformat()

    datasets = []
    for g in result.per_group:
        datasets.append(
            {
                "title": f"{g.label} — calculated data products",
                "dataset_id": {"type": "other", "identifier": f"TODO-dataset-id-{g.key}"},
                "distribution": [
                    {
                        "title": f"{g.label} planned volume",
                        "byte_size": round(g.stored_bytes),  # integer bytes per spec
                        "data_access": "TODO: open | shared | closed",
                    }
                ],
            }
        )

    return {
        "dmp": {
            "title": result.title,
            "language": language,
            "created": today,
            "modified": today,
            "dmp_id": {"type": "other", "identifier": "TODO-register-DOI-on-Zenodo"},
            "contact": {
                "name": "TODO: PI name",
                "mbox": "TODO: pi@institution.example",
                "contact_id": {"type": "orcid", "identifier": "TODO-orcid"},
            },
            "dataset": datasets,
            "extension": [
                {
                    "datacal": {
                        "total_stored_bytes": round(result.total_stored_bytes),
                        "total_transmitted_bytes": round(result.total_transmitted_bytes),
                        "peak_transmit_mbps": round(result.peak_transmit_mbps, 3),
                        "note": "Volumes calculated by DataCal from instrument "
                                "specifications and sampling schedule.",
                    }
                }
            ],
        }
    }
