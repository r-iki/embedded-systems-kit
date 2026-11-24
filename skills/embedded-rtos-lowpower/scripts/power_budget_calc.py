#!/usr/bin/env python3
"""Estimate average current draw and battery life from multi-state duty cycles."""

from __future__ import annotations

import argparse
import json
import sys


def parse_state(spec: str) -> dict[str, float | str]:
    parts = spec.split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid --state '{spec}'. Expected format: name:current_ma:duration_s")
    name = parts[0].strip()
    current_ma = float(parts[1])
    duration_s = float(parts[2])
    if current_ma < 0 or duration_s < 0:
        raise ValueError(f"Negative values are not allowed in --state '{spec}'")
    return {"name": name, "current_ma": current_ma, "duration_s": duration_s}


def calculate_budget(
    battery_mah: float,
    states: list[dict[str, float | str]],
    derating: float = 0.85,
    always_on_ma: float = 0.0,
) -> dict[str, object]:
    total_time_s = sum(float(s["duration_s"]) for s in states)
    if total_time_s <= 0:
        raise ValueError("Total cycle duration across states must be > 0 seconds.")

    weighted_charge_mas = 0.0
    breakdown = []
    for s in states:
        cur = float(s["current_ma"]) + always_on_ma
        dur = float(s["duration_s"])
        charge = cur * dur
        weighted_charge_mas += charge
        breakdown.append({
            "name": s["name"],
            "current_ma": round(cur, 6),
            "duration_s": dur,
            "duty_percent": round(dur * 100.0 / total_time_s, 3),
            "charge_mas": charge,
        })

    for item in breakdown:
        item["energy_share_percent"] = (
            round(float(item["charge_mas"]) * 100.0 / weighted_charge_mas, 2)
            if weighted_charge_mas > 0
            else 0.0
        )

    avg_current_ma = weighted_charge_mas / total_time_s
    usable_mah = battery_mah * derating
    hours = usable_mah / avg_current_ma if avg_current_ma > 0 else float("inf")
    days = hours / 24.0

    return {
        "battery_mah": battery_mah,
        "derating": derating,
        "usable_mah": round(usable_mah, 2),
        "always_on_overhead_ma": always_on_ma,
        "cycle_duration_s": round(total_time_s, 4),
        "average_current_ma": round(avg_current_ma, 6),
        "estimated_hours": round(hours, 2),
        "estimated_days": round(days, 2),
        "estimated_months": round(days / 30.4375, 2),
        "states": breakdown,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate embedded system average current and battery life.")
    parser.add_argument("--battery-mah", type=float, required=True, help="Nominal battery capacity in mAh")
    parser.add_argument("--derating", type=float, default=0.85, help="Usable capacity factor (default: 0.85)")
    parser.add_argument("--always-on-ma", type=float, default=0.0, help="Constant board/LDO quiescent current in mA")
    parser.add_argument(
        "--state",
        action="append",
        required=True,
        help="State profile as name:current_ma:duration_s (repeatable)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    try:
        states = [parse_state(s) for s in args.state]
        result = calculate_budget(args.battery_mah, states, args.derating, args.always_on_ma)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print("=== Embedded Power Budget Estimate ===")
    print(f"  Battery         : {result['battery_mah']} mAh (usable @ {result['derating']}: {result['usable_mah']} mAh)")
    print(f"  Cycle Period    : {result['cycle_duration_s']} s")
    print(f"  Average Current : {result['average_current_ma']} mA ({float(result['average_current_ma']) * 1000.0:.1f} uA)")
    print(f"  Estimated Life  : {result['estimated_days']} days ({result['estimated_months']} months / {result['estimated_hours']} h)")
    print("\nState Breakdown:")
    for item in result["states"]:  # type: ignore[union-attr]
        print(
            f"  - {item['name']:<16} {item['current_ma']:>9.4f} mA x {item['duration_s']:>7.2f} s "
            f"(duty {item['duty_percent']:>6.2f}%, energy share {item['energy_share_percent']:>6.2f}%)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
