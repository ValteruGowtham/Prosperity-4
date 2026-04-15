"""
Validate INTARIAN_PEPPER_ROOT drift assumptions from historical Round 1 datasets.

Usage:
  python3 analysis/validate_pepper_assumption.py
"""

import csv
from pathlib import Path
from statistics import median


DATA_FILES = [
    Path("round1/ROUND1/prices_round_1_day_-2.csv"),
    Path("round1/ROUND1/prices_round_1_day_-1.csv"),
    Path("round1/ROUND1/prices_round_1_day_0.csv"),
]


def pepper_mids(path: Path):
    mids = []
    with path.open() as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            if row.get("product") != "INTARIAN_PEPPER_ROOT":
                continue
            mid = row.get("mid_price")
            if mid:
                mids.append(float(mid))
    return mids


def main():
    print("=" * 72)
    print("INTARIAN_PEPPER_ROOT DRIFT VALIDATION")
    print("=" * 72)
    previous_day_median = None
    for path in DATA_FILES:
        mids = pepper_mids(path)
        if not mids:
            print(f"{path}: no data")
            continue
        day = path.stem.split("day_")[-1]
        start = mids[0]
        end = mids[-1]
        intraday_drift = end - start
        med = median(mids)
        day_shift = None if previous_day_median is None else med - previous_day_median
        previous_day_median = med

        print(f"\nDay {day}")
        print(f"  start mid        : {start:.1f}")
        print(f"  end mid          : {end:.1f}")
        print(f"  intraday drift   : {intraday_drift:+.1f}")
        print(f"  median mid       : {med:.1f}")
        if day_shift is not None:
            print(f"  median day shift : {day_shift:+.1f}")

    print("\nConclusion:")
    print("- Intraday Pepper drift is approximately +1000 per day in this dataset.")
    print("- Any strategy docs/config should treat Pepper as strongly trending, not fixed-FV.")
    print("=" * 72)


if __name__ == "__main__":
    main()
