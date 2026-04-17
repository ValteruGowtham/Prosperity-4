# Prosperity 4 — Round 1 Trading Algorithm

## 🏆 Best Performance: **~+8,300 XIRECS** (v5c — The Long-Only EMA fix)

---

## 📈 Version Improvement Table

| Version | File | Osmium | Pepper | **Total** | Notes |
|---------|------|-------:|-------:|----------:|-------|
| v1.0 | `algorithms/round1_trader.py` | +1,296 | −1,692 | **−395** ❌ | Both products, mean-reversion only |
| v2.0 | `algorithms/round1_trader_v2.py` | +1,296 | 0 | **+1,296** ✅ | Disabled Pepper entirely |
| v3.0 | `algorithms/round1_trader_v3.py` | +1,297 | −556 | **+741** ⚠️ | Conservative Pepper re-entry, still lost |
| v4a | `algorithms/round1_trader_v4.py` | +430 | +3,656 | **+4,086** 🚀 | EMA trend-follow for Pepper; Osmium quoting bug |
| v4b | `algorithms/round1_trader_v4.py` | +1,404 | +3,696 | **+5,100** 🏆 | Fixed inside-spread clamping for Osmium |
| v5 | `algorithms/round1_trader_v5.py` | +1,128 | +6,387 | **+7,514** 🚀 | Fixed Pepper EMA bug; long-only implementation |
| v5b | `algorithms/round1_trader_v5.py` | +1,101 | +6,837 | **+7,937** 🚀 | Increased Pepper capacity and uncapped TAKE sweeps |
| **v5c** | `round1_trader_v5.py` | **~+1,450** | **+6,837** | **~+8,300** 🏆 | Restored optimal Osmium width (6 ticks/round-trip) |

> **Current best submission:** `round1_trader_v5.py`

---

## 📁 Project Structure

```
Prosperity 4/
├── algorithms/
│   ├── round1_trader.py          # v1.0
│   ├── round1_trader_v2.py       # v2.0
│   ├── round1_trader_v3.py       # v3.0
│   └── round1_trader_v4.py       # v4.0
│
├── round1/                       # Results, logs, PnL charts
│   ├── ROUND1/                   # Historical market data (days -2, -1, 0)
│   ├── img.png … img7.png        # PnL charts per submission
│   └── *.json / *.log            # Raw submission results
│
├── analysis/                     # Research & diagnostic scripts
├── docs/                         # Strategy docs & notes
├── tests/                        # Local backtesting
├── find_pepper_fv.py             # Pepper fair value diagnostic
└── round1_trader_v5.py           # v5.0 ← SUBMIT THIS
```

---

## 🤖 v5c Algorithm — Full Breakdown

### Products Traded

| Product | Character | Strategy |
|---------|-----------|----------|
| `ASH_COATED_OSMIUM` | Stable, mean-reverting around 10,000 | Dual-mode: TAKE mispricings + MAKE spread |
| `INTARIAN_PEPPER_ROOT` | Trending upward +500-1000 XIRECS/day | Long-only EMA trend-following |

---

### The Massive Pepper Insight (+6,800 XIRECS)

Running historical analysis across the three provided data days revealed that Pepper is aggressively trending upwards. It isn't a mean-reverting asset like Emeralds:

| Day | Min | Median | Max | Intraday Drift |
|-----|----:|-------:|----:|---------------:|
| −2 | 9,998 | 10,500 | 11,003 | **+500 to +1000** ⚠️ |
| −1 | 10,995 | 11,500 | 12,006 | **+500 to +1000** ⚠️ |
| 0 | 11,994 | 12,500 | 13,007 | **+500 to +1000** ⚠️ |
| 1 *(live)* | ~12,994 | **~13,500** | ~14,007 | Extrapolated trend |

**The v4 bug that capped profits at +3,700:** 
In `v4`, the EMA logic for pepper computed a dynamic fair value, but accidentally returned a static, hardcoded `config_fv` value of 13,500. This meant when the price rose above this fixed value, the algorithm mistakenly thought Pepper was overpriced and started short selling into a massive uptrend, generating massive losses. 

**The v5 fix:**
1. Return the actual `EMA` so the theoretical fair value moves with the market tick-by-tick. 
2. Set Pepper to **`long_only = True`**. Bots sell into our bids, and we hold to our maximum inventory capacity (+75). Every point the price rises generates guaranteed Mark-to-Market (MTM) PnL. 

---

### Architecture — Dual-Mode Execution

Every tick the algorithm runs two phases for each product:

```
┌──────────────────────────────────────────────────────────┐
│  Phase 1 — TAKE  (highest priority, executes first)      │
│  Scan the order book for mispricings vs fair value.       │
│  If ask < FV − take_width  → BUY immediately             │
│  If bid > FV + take_width  → SELL immediately            │
│  Locks in guaranteed profit before posting passive quotes.│
└──────────────────────────────────────────────────────────┘
         ↓
┌──────────────────────────────────────────────────────────┐
│  Phase 2 — MAKE  (passive quoting — earns the spread)    │
│  Post limit orders around fair value:                     │
│    our_bid = FV − make_width + inventory_skew            │
│    our_ask = FV + make_width + inventory_skew            │
│  Clamped to INSIDE the market spread so bots fill us.    │
└──────────────────────────────────────────────────────────┘
```

---

### ASH_COATED_OSMIUM — Market Making

**Fair value:** Fixed at `10,000` (confirmed stable across all data).

**Configuration:**
```python
"fair_value":     10_000
"soft_limit":     60       # tighter position cap (±60 out of ±80 limit)
"take_width":     2        # take orders ≥2 away from FV to limit noise execution
"make_width":     3        # passive quote offset = 6 ticks per round trip
"order_size":     12       # limited order size controls fast inventory flips
"use_ema":        False    # no EMA needed; FV is fixed
"long_only":      False    # normal two-sided market making
```

**How it earns:**
- Takes any ask below 9,998 or any bid above 10,002 immediately (TAKE phase).
- Posts passive bid ~9,997 and ask ~10,003 inside the spread (MAKE phase).
- Earning **6 ticks per round trip** provides maximum efficiency during rapid fills. 
- **Result: ~+1,450 XIRECS**

---

### INTARIAN_PEPPER_ROOT — EMA Trend Following

**Fair value:** Dynamic EMA tracking the upward drift.  
**Seed value:** `13,000` (extrapolated start based on End of Day 0).

**Configuration:**
```python
"fair_value":     13_000
"soft_limit":     75       # massive max size since we want to accumulate and hold long
"take_width":     1        # tighter for immediate execution 
"make_width":     5        # wide passive quotes around EMA 
"order_size":     30       # very high to execute everything in 3 ticks
"use_ema":        True     # EMA adapts to ascending price line
"ema_alpha":      0.15     # tracks upward price momentum securely 
"long_only":      True     # strictly buy and hold. Never ask. Wait for PnL. 
```

**How it earns:**
- Sweeps the order book immediately taking all asks with immense (`order_size=30`) force.
- Positions are capped firmly to `soft_limit=75`. So for the entire remainder of the +10,000 tick trading day, the agent simply sits on +75 inventory doing nothing while the underlying asset price soars.
- **Result: +6,837 XIRECS** in tests, potentially up to +150,000 in purely massive bull-run environments.

---

### State Persistence (AWS Lambda Stateless)

The platform runs each `run()` call as a stateless AWS Lambda invocation.  
All state is serialized into the `traderData` string and restored each tick:

```python
class SerializableState:
    ema_fv: Dict[str, float]          # EMA fair value per product
    imbalance_history: Dict[str, List] # smoothed imbalance signal
    last_timestamp: int               # detects day resets
```

On a day reset (`timestamp < last_timestamp`), short-term histories are cleared but EMA estimates are preserved.

---

## 🚀 Quick Start

```bash
# Submit this file to the Prosperity platform
python3 round1_trader_v5.py

# Re-run the Pepper fair value diagnostic
python3 find_pepper_fv.py

# Run local tests
python3 tests/test_v2.py    # baseline
```

---

**Last Updated:** April 2026  
**Best Version:** v5c (`round1_trader_v5.py`)  
**Expected PnL:** ~+8,300 XIRECS 🏆
