"""DataCal calculation engine — Phase 1 (Plan).

Turns a Campaign into calculated data volumes:
  - per device   (aggregated across that instrument's deployments)
  - per leg       (aggregated across instruments active in that leg)
  - per group     (aggregated by research group)
  - campaign totals, plus the peak near-real-time transmission bandwidth.

Pure function of the Campaign. No I/O, no framework, no global state.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import units
from .models import Campaign, Deployment, Instrument, Leg


@dataclass
class DeploymentVolume:
    instrument_id: str
    leg_id: str
    group: str
    raw_bytes: float
    stored_bytes: float
    transmitted_bytes: float


@dataclass
class Bucket:
    """A named aggregation bucket (one device, one leg, or one group)."""

    key: str
    label: str
    stored_bytes: float = 0.0
    transmitted_bytes: float = 0.0


@dataclass
class CampaignResult:
    title: str
    per_device: list[Bucket] = field(default_factory=list)
    per_leg: list[Bucket] = field(default_factory=list)
    per_group: list[Bucket] = field(default_factory=list)
    total_stored_bytes: float = 0.0
    total_transmitted_bytes: float = 0.0
    peak_transmit_mbps: float = 0.0
    peak_transmit_leg_id: str | None = None

    def to_dict(self) -> dict:
        def buckets(bs: list[Bucket]) -> list[dict]:
            return [
                {
                    "key": b.key,
                    "label": b.label,
                    "stored_bytes": round(b.stored_bytes),
                    "stored_human": units.human_bytes(b.stored_bytes),
                    "transmitted_bytes": round(b.transmitted_bytes),
                }
                for b in bs
            ]

        return {
            "title": self.title,
            "totals": {
                "stored_bytes": round(self.total_stored_bytes),
                "stored_human": units.human_bytes(self.total_stored_bytes),
                "transmitted_bytes": round(self.total_transmitted_bytes),
                "transmitted_human": units.human_bytes(self.total_transmitted_bytes),
                "peak_transmit_mbps": round(self.peak_transmit_mbps, 3),
                "peak_transmit_leg_id": self.peak_transmit_leg_id,
            },
            "per_device": buckets(self.per_device),
            "per_leg": buckets(self.per_leg),
            "per_group": buckets(self.per_group),
        }


def _deployment_volume(inst: Instrument, leg: Leg, dep: Deployment) -> DeploymentVolume:
    duty = dep.duty_cycle if dep.duty_cycle is not None else inst.duty_cycle
    count = dep.count if dep.count is not None else inst.count

    raw = inst.raw_bytes_per_second() * leg.active_seconds * duty * count
    stored = raw / inst.compression_ratio * inst.overhead_factor
    transmitted = stored * inst.transmit_fraction
    return DeploymentVolume(
        instrument_id=inst.id,
        leg_id=leg.id,
        group=inst.group,
        raw_bytes=raw,
        stored_bytes=stored,
        transmitted_bytes=transmitted,
    )


def calculate(campaign: Campaign) -> CampaignResult:
    """Calculate all volume breakdowns for a campaign."""
    volumes = [
        _deployment_volume(campaign.instrument(d.instrument_id), campaign.leg(d.leg_id), d)
        for d in campaign.deployments
    ]

    device: dict[str, Bucket] = {}
    leg: dict[str, Bucket] = {}
    group: dict[str, Bucket] = {}
    leg_transmitted: dict[str, float] = {}

    for v in volumes:
        inst = campaign.instrument(v.instrument_id)
        d = device.setdefault(inst.id, Bucket(inst.id, inst.name))
        d.stored_bytes += v.stored_bytes
        d.transmitted_bytes += v.transmitted_bytes

        lg = campaign.leg(v.leg_id)
        lb = leg.setdefault(lg.id, Bucket(lg.id, lg.name))
        lb.stored_bytes += v.stored_bytes
        lb.transmitted_bytes += v.transmitted_bytes

        g = group.setdefault(v.group, Bucket(v.group, v.group))
        g.stored_bytes += v.stored_bytes
        g.transmitted_bytes += v.transmitted_bytes

        leg_transmitted[v.leg_id] = leg_transmitted.get(v.leg_id, 0.0) + v.transmitted_bytes

    # Peak near-real-time bandwidth: the busiest leg's transmitted volume spread
    # across that leg's duration. This is the link size the campaign must size for.
    peak_mbps = 0.0
    peak_leg = None
    for leg_id, transmitted in leg_transmitted.items():
        if transmitted <= 0:
            continue
        mbps = units.bytes_to_mbps(transmitted, campaign.leg(leg_id).active_seconds)
        if mbps > peak_mbps:
            peak_mbps, peak_leg = mbps, leg_id

    result = CampaignResult(title=campaign.title)
    # Preserve declaration order for stable, reviewable output.
    result.per_device = [device[i.id] for i in campaign.instruments if i.id in device]
    result.per_leg = [leg[l.id] for l in campaign.legs if l.id in leg]
    result.per_group = sorted(group.values(), key=lambda b: b.label)
    result.total_stored_bytes = sum(v.stored_bytes for v in volumes)
    result.total_transmitted_bytes = sum(v.transmitted_bytes for v in volumes)
    result.peak_transmit_mbps = peak_mbps
    result.peak_transmit_leg_id = peak_leg
    return result
