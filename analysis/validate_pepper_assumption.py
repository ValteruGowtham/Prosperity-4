"""
Validate INTARIAN_PEPPER_ROOT drift assumptions from historical Round 1 datasets.

Usage:
  python3 analysis/validate_pepper_assumption.py
"""

import csv
import argparse
from pathlib import Path
from statistics import mean, median


def data_files(data_dir: Path):
    return [
        data_dir / "prices_round_1_day_-2.csv",
        data_dir / "prices_round_1_day_-1.csv",
        data_dir / "prices_round_1_day_0.csv",
    ]


def pepper_mids(path: Path):
    mids = []
    with path.open() as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            if row.get("product") != "INTARIAN_PEPPER_ROOT":
                continue
            mid = row.get("mid_price")
            if mid is not None and mid != "":
                mids.append(float(mid))
    return mids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        default="round1/ROUND1",
        help="Directory containing prices_round_1_day_*.csv files",
    )
    args = parser.parse_args()
    files = data_files(Path(args.data_dir))

    print("=" * 72)
    print("INTARIAN_PEPPER_ROOT DRIFT VALIDATION")
    print("=" * 72)
    previous_day_median = None
    drifts = []
    for path in files:
        mids = pepper_mids(path)
        if not mids:
            print(f"{path}: no data")
            continue
        day = path.stem.split("day_")[-1]
        start = mids[0]
        end = mids[-1]
        intraday_drift = end - start
        drifts.append(intraday_drift)
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

    avg_drift = mean(drifts) if drifts else 0.0
    print("\nConclusion:")
    print(f"- Average intraday Pepper drift is {avg_drift:+.1f} per day in this dataset.")
    print("- Any strategy docs/config should treat Pepper as strongly trending, not fixed-FV.")
    print("=" * 72)


if __name__ == "__main__":
    main()
