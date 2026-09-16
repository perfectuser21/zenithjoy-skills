#!/usr/bin/env python3
"""Allocate weekly/daily WeChat Moments content counts.

This helper performs deterministic integer allocation for:
- weekly customer-stage plan from a weekly total and a1-a4 counts
- optional stage-priority weighting from Feishu content strategy configuration
- default daily totals across Monday-Sunday, with weekend days higher when feasible
- daily stage allocation from current CRM counts
- deviation checking between weekly and daily ratios

Example:
python scripts/allocate_schedule.py --weekly-total 50 --week-counts 40 30 20 10 \
  --daily-total 7 --today-counts 30 35 25 10 --threshold 0.1
"""

from __future__ import annotations

import argparse
import json
import math
from typing import Dict, List, Tuple

STAGES = ["a1", "a2", "a3", "a4"]
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def validate_counts(counts: List[int], label: str) -> None:
    if len(counts) != 4:
        raise ValueError(f"{label} must contain exactly four counts: a1 a2 a3 a4")
    if any(c < 0 for c in counts):
        raise ValueError(f"{label} cannot contain negative values")
    if sum(counts) == 0:
        raise ValueError(
            f"{label} total is zero; repair the Feishu CRM snapshot or use an explicitly approved temporary distribution"
        )


def ratios_from_counts(counts: List[int]) -> Dict[str, float]:
    validate_counts(counts, "counts")
    total = sum(counts)
    return {stage: counts[i] / total for i, stage in enumerate(STAGES)}


def weighted_ratios(ratios: Dict[str, float], weights: List[float]) -> Dict[str, float]:
    if len(weights) != 4:
        raise ValueError("stage-weights must contain exactly four values: a1 a2 a3 a4")
    if any(weight < 0 for weight in weights):
        raise ValueError("stage-weights cannot contain negative values")
    scores = {stage: ratios[stage] * weights[i] for i, stage in enumerate(STAGES)}
    total = sum(scores.values())
    if total == 0:
        raise ValueError("weighted stage total is zero; check CRM counts and stage-weights")
    return {stage: scores[stage] / total for stage in STAGES}


def largest_remainder_allocate(total: int, ratios: Dict[str, float]) -> Dict[str, int]:
    if total < 0:
        raise ValueError("total cannot be negative")
    raw: List[Tuple[str, float]] = [(key, total * ratios[key]) for key in ratios]
    floors = {key: int(math.floor(value)) for key, value in raw}
    remaining = total - sum(floors.values())
    ranked = sorted(raw, key=lambda item: (item[1] - math.floor(item[1]), item[1]), reverse=True)
    result = dict(floors)
    for i in range(remaining):
        result[ranked[i % len(ranked)][0]] += 1
    return result


def daily_totals(weekly_total: int) -> Dict[str, int]:
    """Return a Monday-Sunday plan.

    Preference order:
    1. sum equals weekly_total
    2. weekend days are not lower than weekdays
    3. weekend days are ideally 1-2 higher than weekday level
    4. weekdays are as balanced as possible
    """
    if weekly_total < 0:
        raise ValueError("weekly_total cannot be negative")
    if weekly_total == 0:
        return {day: 0 for day in DAYS}

    best = None
    best_score = None
    max_day = max(weekly_total, 1)

    # Brute force compact families: weekdays use x or x+1; weekends use y or y+1.
    for x in range(max_day + 1):
        for wd_plus_count in range(6):
            weekday_values = [x + 1] * wd_plus_count + [x] * (5 - wd_plus_count)
            # Place the slightly lower weekday on Friday first when possible, keeping Mon-Thu steady.
            weekday_values = sorted(weekday_values, reverse=True)
            for y in range(max_day + 1):
                for we_plus_count in range(3):
                    weekend_values = [y + 1] * we_plus_count + [y] * (2 - we_plus_count)
                    total = sum(weekday_values) + sum(weekend_values)
                    if total != weekly_total:
                        continue
                    weekday_min, weekday_max = min(weekday_values), max(weekday_values)
                    weekend_min, weekend_max = min(weekend_values), max(weekend_values)
                    avg_weekday = sum(weekday_values) / 5
                    weekend_bonus = weekend_min - avg_weekday
                    score = 0
                    score += 1000 * max(0, weekday_max - weekday_min - 1)
                    score += 1000 * max(0, weekend_max - weekend_min - 1)
                    if weekend_min < weekday_max:
                        score += 500
                    if 1 <= weekend_bonus <= 2:
                        score -= 100
                    else:
                        score += abs(1.5 - weekend_bonus) * 10
                    # Prefer Saturday and Sunday equal or close.
                    score += weekend_max - weekend_min
                    if best_score is None or score < best_score:
                        best_score = score
                        best = weekday_values + weekend_values

    if best is None:
        # Fallback: even split, then add remainder from weekend backward.
        base, rem = divmod(weekly_total, 7)
        values = [base] * 7
        order = [5, 6, 0, 1, 2, 3, 4]
        for i in range(rem):
            values[order[i]] += 1
        best = values

    return {day: best[i] for i, day in enumerate(DAYS)}


def deviations(week_ratios: Dict[str, float], today_ratios: Dict[str, float]) -> Dict[str, float]:
    return {stage: abs(today_ratios[stage] - week_ratios[stage]) for stage in STAGES}


def main() -> None:
    parser = argparse.ArgumentParser(description="Allocate WeChat Moments schedule counts.")
    parser.add_argument("--weekly-total", type=int, required=True)
    parser.add_argument("--week-counts", type=int, nargs=4, metavar=("A1", "A2", "A3", "A4"), required=True)
    parser.add_argument("--daily-total", type=int, default=None)
    parser.add_argument("--today-counts", type=int, nargs=4, metavar=("A1", "A2", "A3", "A4"), default=None)
    parser.add_argument(
        "--stage-weights",
        type=float,
        nargs=4,
        metavar=("A1", "A2", "A3", "A4"),
        default=[1.0, 1.0, 1.0, 1.0],
        help="Optional content-priority weights from Feishu Base; defaults to 1 1 1 1",
    )
    parser.add_argument("--threshold", type=float, default=0.10, help="Deviation threshold as decimal, default 0.10")
    args = parser.parse_args()

    if args.weekly_total < 0:
        raise ValueError("weekly total cannot be negative")
    validate_counts(args.week_counts, "week-counts")

    week_ratios = ratios_from_counts(args.week_counts)
    week_content_ratios = weighted_ratios(week_ratios, args.stage_weights)
    result = {
        "weekly_total": args.weekly_total,
        "week_counts": dict(zip(STAGES, args.week_counts)),
        "week_ratios": week_ratios,
        "stage_weights": dict(zip(STAGES, args.stage_weights)),
        "week_content_ratios": week_content_ratios,
        "week_stage_plan": largest_remainder_allocate(args.weekly_total, week_content_ratios),
        "daily_totals": daily_totals(args.weekly_total),
    }

    if args.today_counts is not None:
        validate_counts(args.today_counts, "today-counts")
        today_ratios = ratios_from_counts(args.today_counts)
        devs = deviations(week_ratios, today_ratios)
        trigger = any(value >= args.threshold for value in devs.values())
        today_content_ratios = weighted_ratios(today_ratios, args.stage_weights)
        base_ratios = today_content_ratios if trigger else week_content_ratios
        if args.daily_total is None:
            raise ValueError("--daily-total is required when --today-counts is supplied")
        result.update({
            "today_counts": dict(zip(STAGES, args.today_counts)),
            "today_ratios": today_ratios,
            "today_content_ratios": today_content_ratios,
            "deviations": devs,
            "threshold": args.threshold,
            "daily_calibration_triggered": trigger,
            "daily_stage_plan_basis": "today_ratios" if trigger else "week_ratios",
            "daily_total": args.daily_total,
            "daily_stage_plan": largest_remainder_allocate(args.daily_total, base_ratios),
        })

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
