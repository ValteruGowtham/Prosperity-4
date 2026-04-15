# v4b Hardening Notes

This update hardens `algorithms/round1_trader_v4.py` against regime shifts and adverse selection.

## What changed

1. **Pepper fair value is now truly adaptive**
   - `use_ema=True` now returns EMA-driven fair value with a small anchor blend.
   - Added short-horizon trend projection on top of EMA.

2. **Pepper short-side guardrails**
   - Added `max_short` cap.
   - In strong uptrend, passive sell posting can be disabled.
   - Sell-taking threshold is stricter in strong uptrend.

3. **Regime-aware risk controls**
   - Per-product mark-to-market proxy tracking.
   - Per-product drawdown brake (`kill_switch`) that switches to risk-reduction-only orders.
   - Recovery threshold to re-enable normal quoting.

4. **Quote quality controls**
   - Dynamic make/take widths from observed spread.
   - Dynamic order sizing from top-of-book liquidity.
   - Fill-toxicity score from own trades; when toxic, widen quotes and reduce size.

## Data assumption alignment

Historical Round 1 Pepper data shows intraday drift closer to **~+1000/day** than +500/day.

Reproducible check:

```bash
python3 analysis/validate_pepper_assumption.py
```

## Standardized version comparison

Use one shared pipeline for result JSONs:

```bash
python3 analysis/compare_versions.py <v2.json> <v3.json> <v4b.json>
```

Reported metrics:
- Final PnL
- Max drawdown
- Adverse-selection score
- Fill-asymmetry proxy
- Inventory-extreme proxy
