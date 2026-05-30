"""Command-line entry point: python -m datacal <campaign.json> [--madmp]

Prints a human-readable volume breakdown. With --madmp, prints the maDMP JSON.
"""

from __future__ import annotations

import json
import sys

from . import units
from .engine import calculate
from .madmp import to_madmp
from .models import campaign_from_dict


def _print_summary(result) -> None:
    print(f"\n{result.title}")
    print("=" * len(result.title))

    print("\nPer research group:")
    for b in result.per_group:
        print(f"  {b.label:<28} {units.human_bytes(b.stored_bytes):>12}")

    print("\nPer expedition leg:")
    for b in result.per_leg:
        print(f"  {b.label:<28} {units.human_bytes(b.stored_bytes):>12}")

    print("\nPer instrument:")
    for b in result.per_device:
        print(f"  {b.label:<28} {units.human_bytes(b.stored_bytes):>12}")

    print("\nTotals:")
    print(f"  Stored volume               {units.human_bytes(result.total_stored_bytes):>12}")
    print(f"  Near-real-time transmitted  {units.human_bytes(result.total_transmitted_bytes):>12}")
    if result.peak_transmit_leg_id:
        print(f"  Peak link bandwidth         {result.peak_transmit_mbps:>9.2f} Mbps"
              f"  (leg {result.peak_transmit_leg_id})")
    print()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    path = argv[0]
    as_madmp = "--madmp" in argv[1:]

    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {path}: {exc}", file=sys.stderr)
        return 2

    try:
        campaign = campaign_from_dict(data)
    except ValueError as exc:
        print(f"error: invalid campaign: {exc}", file=sys.stderr)
        return 2

    result = calculate(campaign)
    if as_madmp:
        print(json.dumps(to_madmp(result), indent=2))
    else:
        _print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
