"""DataCal domain models — Phase 1 (Plan).

Framework-independent. No FastAPI, no SQLAlchemy, no I/O. This is the audited
core: a scientist must be able to read these rules and agree the arithmetic is
correct. Everything else (API, database, React forms) wraps this.

PRODUCTION MODEL
----------------
An instrument produces a *raw* data rate (bytes/second). Two ways to declare it:

  - "rate"   : you know the rate directly (e.g. an HD camera = 50 MB/s).
  - "sample" : raw_rate = channels * sampling_hz * (bit_depth / 8)
               (e.g. 4 channels * 100 Hz * 24-bit = 1200 B/s).

Raw rate is then modified to a *stored* volume over a deployment:

    raw      = raw_rate * active_seconds * duty_cycle * count
    stored   = raw / compression_ratio * overhead_factor
    transmit = stored * transmit_fraction

  duty_cycle       fraction of the deployment the instrument actually records
                   (e.g. profiling every 6 h at 10 min/profile -> ~0.028).
  count            number of identical units of this instrument.
  compression_ratio  >= 1.0; raw/ratio. 1.0 = none, 2.0 = halves it.
  overhead_factor    >= 1.0; multiplies stored to account for metadata and
                     derived/processed products kept alongside raw (L0+L1+L2).
  transmit_fraction  0..1; portion of stored data sent in near-real-time over
                     the link (the rest is delayed-mode / physically retrieved).

Every assumption above is explicit and overridable. None of it is hidden.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from . import units

ProductionModel = Literal["rate", "sample"]


@dataclass(frozen=True)
class Leg:
    """A time segment of a campaign (an expedition leg)."""

    id: str
    name: str
    duration_days: float

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Leg.id must be non-empty")
        if self.duration_days <= 0:
            raise ValueError(f"Leg {self.id!r}: duration_days must be > 0")

    @property
    def active_seconds(self) -> float:
        return self.duration_days * units.SECONDS_PER_DAY


@dataclass
class Instrument:
    """A data-producing instrument and its production characteristics."""

    id: str
    name: str
    group: str
    model: ProductionModel

    # rate model
    data_rate_bytes_per_s: float | None = None
    # sample model
    channels: int | None = None
    sampling_hz: float | None = None
    bit_depth: int | None = None

    # modifiers (defaults = no effect)
    duty_cycle: float = 1.0
    count: int = 1
    compression_ratio: float = 1.0
    overhead_factor: float = 1.0
    transmit_fraction: float = 0.0

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Instrument.id must be non-empty")
        if self.model not in ("rate", "sample"):
            raise ValueError(f"Instrument {self.id!r}: model must be 'rate' or 'sample'")

        if self.model == "rate":
            if self.data_rate_bytes_per_s is None:
                raise ValueError(f"Instrument {self.id!r}: rate model requires data_rate_bytes_per_s")
            if self.data_rate_bytes_per_s < 0:
                raise ValueError(f"Instrument {self.id!r}: data_rate_bytes_per_s must be >= 0")
        else:  # sample
            missing = [n for n, v in (("channels", self.channels),
                                      ("sampling_hz", self.sampling_hz),
                                      ("bit_depth", self.bit_depth)) if v is None]
            if missing:
                raise ValueError(f"Instrument {self.id!r}: sample model requires {missing}")
            if self.channels < 1:
                raise ValueError(f"Instrument {self.id!r}: channels must be >= 1")
            if self.sampling_hz <= 0:
                raise ValueError(f"Instrument {self.id!r}: sampling_hz must be > 0")
            if self.bit_depth < 1:
                raise ValueError(f"Instrument {self.id!r}: bit_depth must be >= 1")

        if not (0.0 <= self.duty_cycle <= 1.0):
            raise ValueError(f"Instrument {self.id!r}: duty_cycle must be in [0, 1]")
        if self.count < 1:
            raise ValueError(f"Instrument {self.id!r}: count must be >= 1")
        if self.compression_ratio < 1.0:
            raise ValueError(f"Instrument {self.id!r}: compression_ratio must be >= 1.0")
        if self.overhead_factor < 1.0:
            raise ValueError(f"Instrument {self.id!r}: overhead_factor must be >= 1.0")
        if not (0.0 <= self.transmit_fraction <= 1.0):
            raise ValueError(f"Instrument {self.id!r}: transmit_fraction must be in [0, 1]")

    def raw_bytes_per_second(self) -> float:
        """Raw acquisition rate before duty cycle, count, compression or overhead."""
        if self.model == "rate":
            return float(self.data_rate_bytes_per_s)
        return self.channels * self.sampling_hz * (self.bit_depth / units.BITS_PER_BYTE)


@dataclass
class Deployment:
    """Join between an instrument and a leg it is active in.

    Optional overrides let the same instrument run with a different duty cycle
    or unit count on different legs without redefining the instrument.
    """

    instrument_id: str
    leg_id: str
    duty_cycle: float | None = None
    count: int | None = None

    def __post_init__(self) -> None:
        if self.duty_cycle is not None and not (0.0 <= self.duty_cycle <= 1.0):
            raise ValueError("Deployment.duty_cycle override must be in [0, 1]")
        if self.count is not None and self.count < 1:
            raise ValueError("Deployment.count override must be >= 1")


@dataclass
class Campaign:
    """A field campaign: legs, instruments, and their deployments."""

    title: str
    legs: list[Leg] = field(default_factory=list)
    instruments: list[Instrument] = field(default_factory=list)
    deployments: list[Deployment] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._validate_unique([l.id for l in self.legs], "leg")
        self._validate_unique([i.id for i in self.instruments], "instrument")
        leg_ids = {l.id for l in self.legs}
        inst_ids = {i.id for i in self.instruments}
        for d in self.deployments:
            if d.instrument_id not in inst_ids:
                raise ValueError(f"Deployment references unknown instrument {d.instrument_id!r}")
            if d.leg_id not in leg_ids:
                raise ValueError(f"Deployment references unknown leg {d.leg_id!r}")

    @staticmethod
    def _validate_unique(ids: list[str], kind: str) -> None:
        seen = set()
        for i in ids:
            if i in seen:
                raise ValueError(f"Duplicate {kind} id {i!r}")
            seen.add(i)

    def instrument(self, instrument_id: str) -> Instrument:
        for i in self.instruments:
            if i.id == instrument_id:
                return i
        raise KeyError(instrument_id)

    def leg(self, leg_id: str) -> Leg:
        for l in self.legs:
            if l.id == leg_id:
                return l
        raise KeyError(leg_id)


def campaign_from_dict(data: dict) -> Campaign:
    """Build a Campaign from a plain dict (e.g. parsed JSON). Validates on construction."""
    try:
        legs = [Leg(**l) for l in data["legs"]]
        instruments = [Instrument(**i) for i in data["instruments"]]
        deployments = [Deployment(**d) for d in data["deployments"]]
    except KeyError as exc:
        raise ValueError(f"Campaign input missing required key: {exc}") from exc
    except TypeError as exc:
        raise ValueError(f"Campaign input has an invalid field: {exc}") from exc
    return Campaign(title=data.get("title", "Untitled campaign"),
                    legs=legs, instruments=instruments, deployments=deployments)
