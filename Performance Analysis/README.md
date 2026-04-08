# Performance Analysis

PNL graphs and analysis for each version of the trading algorithm.

---

## v1.0 — Mean-Reversion Market Maker

**Final PNL**: ~+120 | **Max Drawdown**: ~-500 | **Status**: ERROR

### Issues Identified
- Deep U-shaped curve — massive drawdown early on
- Took ~170K iterations to recover from losses
- Extremely jagged PNL — too much risk per trade
- Barely profitable after all the volatility

### Root Causes
1. Aggressively taking liquidity (paying spread instead of earning it)
2. No minimum deviation threshold — traded noise
3. No momentum filter — fought against trends
4. Large order sizes amplified losses

![v1.0 PNL Graph](v1.0/v1-pnl-graph.png)

---

## v2.0 — Conservative Mean-Reversion Market Maker

**Final PNL**: +800.13 | **Max Drawdown**: ~-200 | **Status**: FINISHED

### Improvements Over v1.0
- **6.7x better PNL** (+800 vs +120)
- **60% smaller drawdowns** (-200 vs -500)
- No errors — platform integration fixed
- Steady upward trend with smoother curve

### Remaining Issues
1. EMERALDS PNL flatlined at ~55 — orders too conservative
2. Late-game plateau after ~175K iterations — fair value drift
3. Two significant dips (~99.5K and ~161.9K)
4. TOMATOES did all the heavy lifting

### Root Causes
1. AWS Lambda stateless — state lost between invocations
2. Sliding window median caused fair value drift
3. EMERALDS half-spread=5 too wide for tight market
4. Momentum threshold too aggressive

![v2.0 PNL Graph](v2.0/v2-pnl-graph.png)

---

## v3.0 — Stateless-Aware Market Maker

**Expected Improvements** (pending platform results):
- Full state persistence via `traderData`
- EMA-based fair value (no drift)
- EMERALDS optimized for more fills
- Relaxed momentum filter
- Dual position tracking

### Changes Summary

| Metric | v1.0 | v2.0 | v3.0 |
|--------|------|------|------|
| Final PNL | +120 | +800.13 | TBD |
| Max Drawdown | -500 | -200 | TBD |
| EMERALDS PNL | ~0 | ~55 | TBD |
| TOMATOES PNL | ~120 | ~745 | TBD |
| Status | ERROR | FINISHED | TBD |
