"""
DIAGNOSTIC SCRIPT: Find INTARIAN_PEPPER_ROOT true fair value
Run this BEFORE submitting to determine PEPPER_FAIR_VALUE config.

Usage:
    python3 find_pepper_fv.py
"""

import csv
import statistics
from collections import Counter

FILES = [
    "round1/ROUND1/prices_round_1_day_-2.csv",
    "round1/ROUND1/prices_round_1_day_-1.csv",
    "round1/ROUND1/prices_round_1_day_0.csv",
]

for filepath in FILES:
    mids, spreads, bids, asks = [], [], [], []
    try:
        with open(filepath) as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                if row.get("product") != "INTARIAN_PEPPER_ROOT":
                    continue
                mid = float(row["mid_price"]) if row.get("mid_price") else None
                b   = float(row["bid_price_1"]) if row.get("bid_price_1") else None
                a   = float(row["ask_price_1"]) if row.get("ask_price_1") else None
                if mid and mid > 0:
                    mids.append(mid)
                if b and a and b > 0 and a > 0:
                    spreads.append(a - b)
                    bids.append(b)
                    asks.append(a)

        day = filepath.split("day_")[-1].replace(".csv", "")
        print(f"\n{'='*60}")
        print(f"  Day {day}: INTARIAN_PEPPER_ROOT")
        print(f"{'='*60}")
        print(f"  Data points:  {len(mids)}")
        print(f"  Min price:    {min(mids):.1f}")
        print(f"  Max price:    {max(mids):.1f}")
        print(f"  Mean price:   {statistics.mean(mids):.2f}")
        print(f"  Median price: {statistics.median(mids):.2f}   ← LIKELY TRUE FV")
        print(f"  Stdev:        {statistics.stdev(mids):.2f}")
        print(f"  Avg spread:   {statistics.mean(spreads):.2f}")
        print(f"  Median bid:   {statistics.median(bids):.2f}")
        print(f"  Median ask:   {statistics.median(asks):.2f}")

        # Check if price is stable (like Emeralds) or drifting
        half = len(mids) // 2
        first_half_mean = statistics.mean(mids[:half])
        second_half_mean = statistics.mean(mids[half:])
        drift = second_half_mean - first_half_mean
        print(f"\n  First-half mean:  {first_half_mean:.2f}")
        print(f"  Second-half mean: {second_half_mean:.2f}")
        print(f"  Intraday drift:   {drift:+.2f}")

        if abs(drift) < 20:
            print(f"  ✅ LOW DRIFT → stable FV, use median as hardcoded value")
        else:
            print(f"  ⚠️  HIGH DRIFT → investigate further")

        # Most common price bucket (round to nearest 10)
        rounded = [round(m / 5) * 5 for m in mids]
        most_common_price, count = Counter(rounded).most_common(1)[0]
        print(f"\n  Most common price bucket: {most_common_price} ({count}x)")
        print(f"\n  ★ RECOMMENDED FAIR_VALUE: {int(statistics.median(mids))}")

    except FileNotFoundError:
        print(f"File not found: {filepath}")
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

print("\n" + "="*60)
print("  Set PEPPER_FAIR_VALUE to the Recommended value above")
print("  in round1_trader_v4.py before submitting!")
print("="*60)
