"""
Standardized metrics pipeline for Prosperity submission result JSON files.

Computes:
- Total and per-product final PnL
- Max drawdown (total and per-product)
- Adverse-selection score (PnL-negative-event ratio)
- Fill-asymmetry proxy (imbalance of positive vs negative PnL events)
- Inventory-extreme proxy (inferred from PnL/price slope in rolling windows)

Usage:
  python3 analysis/compare_versions.py round1/v2.json round1/v3.json round1/v4b.json
"""

import argparse
import csv
import json
from io import StringIO
from pathlib import Path
from statistics import mean

DELTA_EPSILON = 1e-9


def drawdown(values):
    if not values:
        return 0.0
    peak = values[0]
    max_dd = 0.0
    for v in values:
        peak = max(peak, v)
        max_dd = max(max_dd, peak - v)
    return max_dd


def event_metrics(series):
    if len(series) < 2:
        return 0.0, 0.0
    deltas = [series[i] - series[i - 1] for i in range(1, len(series)) if abs(series[i] - series[i - 1]) > DELTA_EPSILON]
    if not deltas:
        return 0.0, 0.0
    neg = sum(1 for d in deltas if d < 0)
    pos = sum(1 for d in deltas if d > 0)
    total = max(1, neg + pos)
    adverse = neg / total
    asymmetry = abs(pos - neg) / total
    return adverse, asymmetry


def inferred_inventory_extreme(prices, pnls, window=100):
    if len(prices) < window or len(pnls) < window:
        return 0.0
    inferred = []
    series_len = min(len(prices), len(pnls))
    for i in range(window, series_len + 1, window):
        p0, p1 = prices[i - window], prices[i - 1]
        l0, l1 = pnls[i - window], pnls[i - 1]
        dp = p1 - p0
        dl = l1 - l0
        if abs(dp) < DELTA_EPSILON:
            inferred.append(0.0)
        else:
            inferred.append(abs(dl / dp))
    return max(inferred) if inferred else 0.0


def parse_result(path: Path):
    data = json.loads(path.read_text())
    activities = data.get("activitiesLog")
    if not activities:
        raise ValueError(f"{path}: missing activitiesLog")
    rows = list(csv.DictReader(StringIO(activities), delimiter=";"))

    by_product = {}
    total_by_ts = {}
    for r in rows:
        p = r["product"]
        ts = int(r["timestamp"])
        pnl = float(r["profit_and_loss"])
        total_by_ts[ts] = total_by_ts.get(ts, 0.0) + pnl
        by_product.setdefault(p, {"pnl": [], "mid": []})
        by_product[p]["pnl"].append(pnl)
        by_product[p]["mid"].append(float(r["mid_price"]))

    product_metrics = {}
    for product, payload in by_product.items():
        pnl_series = payload["pnl"]
        mid_series = payload["mid"]
        adverse, asymmetry = event_metrics(pnl_series)
        product_metrics[product] = {
            "final_pnl": pnl_series[-1] if pnl_series else 0.0,
            "max_drawdown": drawdown(pnl_series),
            "adverse_selection_score": adverse,
            "fill_asymmetry_proxy": asymmetry,
            "inventory_extreme_proxy": inferred_inventory_extreme(mid_series, pnl_series),
        }

    total_series = [total_by_ts[t] for t in sorted(total_by_ts)] if total_by_ts else []
    total_adverse, total_asymmetry = event_metrics(total_series)

    return {
        "file": str(path),
        "final_pnl": float(data.get("profit", total_series[-1] if total_series else 0.0)),
        "max_drawdown": drawdown(total_series),
        "adverse_selection_score": total_adverse,
        "fill_asymmetry_proxy": total_asymmetry,
        "products": product_metrics,
    }


def print_report(results):
    print("=" * 120)
    print("STANDARDIZED VERSION COMPARISON")
    print("=" * 120)
    headers = (
        "file",
        "final_pnl",
        "max_drawdown",
        "adverse_selection_score",
        "fill_asymmetry_proxy",
    )
    print(
        f"{headers[0]:55} {headers[1]:>12} {headers[2]:>14} {headers[3]:>25} {headers[4]:>22}"
    )
    print("-" * 120)
    for r in results:
        print(
            f"{Path(r['file']).name:55} "
            f"{r['final_pnl']:12.2f} "
            f"{r['max_drawdown']:14.2f} "
            f"{r['adverse_selection_score']:25.3f} "
            f"{r['fill_asymmetry_proxy']:22.3f}"
        )
    print("\nPer-product details:")
    for r in results:
        print(f"\n{Path(r['file']).name}")
        for p, m in r["products"].items():
            print(
                f"  {p:24} pnl={m['final_pnl']:9.2f} "
                f"dd={m['max_drawdown']:9.2f} "
                f"adv={m['adverse_selection_score']:.3f} "
                f"asym={m['fill_asymmetry_proxy']:.3f} "
                f"inv_proxy={m['inventory_extreme_proxy']:.2f}"
            )
    print("=" * 120)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("result_json", nargs="+", help="Submission result JSON files")
    args = parser.parse_args()

    results = [parse_result(Path(p)) for p in args.result_json]
    print_report(results)

    pnls = [r["final_pnl"] for r in results]
    if pnls:
        print(f"\nPnL summary: min={min(pnls):.2f} max={max(pnls):.2f} avg={mean(pnls):.2f}")


if __name__ == "__main__":
    main()
