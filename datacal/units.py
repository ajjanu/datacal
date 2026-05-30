"""Unit handling for DataCal.

Two deliberate conventions, chosen because mixing them up is the single most
common reason spreadsheet volume estimates are wrong:

1. STORAGE volume is measured in **bytes**, reported in **decimal SI** multiples
   (1 GB = 1_000_000_000 bytes). This matches how storage vendors quote capacity
   and how funders phrase DMP storage questions. Binary multiples (GiB = 2**30)
   are NOT used for reporting; if you need them, convert explicitly.

2. TRANSMISSION bandwidth is measured in **bits per second**, reported in
   **Mbit/s (Mbps)**. Satellite and network links are specified in bits, not
   bytes. 1 byte = 8 bits. Reporting a transmission requirement in "MB/s" is a
   factor-of-8 error that DataCal must never make.
"""

from __future__ import annotations

SECONDS_PER_DAY: int = 86_400
BITS_PER_BYTE: int = 8

# Decimal SI byte multiples.
KB = 1_000
MB = 1_000_000
GB = 1_000_000_000
TB = 1_000_000_000_000
PB = 1_000_000_000_000_000

_BYTE_UNITS = (("PB", PB), ("TB", TB), ("GB", GB), ("MB", MB), ("KB", KB), ("B", 1))


def bytes_to(value_bytes: float, unit: str) -> float:
    """Convert a byte count to a named decimal-SI unit ('B','KB','MB','GB','TB','PB')."""
    factors = {name: factor for name, factor in _BYTE_UNITS}
    if unit not in factors:
        raise ValueError(f"Unknown byte unit {unit!r}; expected one of {list(factors)}")
    return value_bytes / factors[unit]


def human_bytes(value_bytes: float, precision: int = 2) -> str:
    """Human-readable decimal-SI string, e.g. 864_000_000_000 -> '864.00 GB'."""
    if value_bytes < 0:
        raise ValueError("byte count cannot be negative")
    for name, factor in _BYTE_UNITS:
        if value_bytes >= factor or name == "B":
            return f"{value_bytes / factor:.{precision}f} {name}"
    return f"{value_bytes:.{precision}f} B"


def bytes_to_mbps(transmitted_bytes: float, over_seconds: float) -> float:
    """Average sustained bandwidth, in Mbit/s, to move `transmitted_bytes` in `over_seconds`."""
    if over_seconds <= 0:
        raise ValueError("transmission window must be > 0 seconds")
    return (transmitted_bytes * BITS_PER_BYTE) / over_seconds / 1_000_000
