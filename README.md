# Prosperity 4 — Round 1 Trading Algorithm

## 🏆 Best Performance: **+5,099 XIRECS** (v4 — fixed clamp)

---

## 📈 Version Improvement Table

| Version | File | Osmium | Pepper | **Total** | Notes |
|---------|------|-------:|-------:|----------:|-------|
| v1.0 | `algorithms/round1_trader.py` | +1,296 | −1,692 | **−395** ❌ | Both products, mean-reversion only |
| v2.0 | `algorithms/round1_trader_v2.py` | +1,296 | 0 | **+1,296** ✅ | Disabled Pepper entirely |
| v3.0 | `algorithms/round1_trader_v3.py` | +1,297 | −556 | **+741** ⚠️ | Conservative Pepper re-entry, still lost |
| v4a | `algorithms/round1_trader_v4.py` | +430 | +3,656 | **+4,086** 🚀 | EMA trend-follow for Pepper; Osmium passive-quoting bug |
| **v4b** | `algorithms/round1_trader_v4.py` | **+1,404** | **+3,696** | **+5,100** 🏆 | Fixed inside-spread clamping for Osmium |

> **Current best submission:** `algorithms/round1_trader_v4.py`

---

## 📁 Project Structure

```
Prosperity 4/
├── algorithms/
│   ├── round1_trader.py          # v1.0
│   ├── round1_trader_v2.py       # v2.0
│   ├── round1_trader_v3.py       # v3.0
│   └── round1_trader_v4.py       # v4.0 ← SUBMIT THIS
│
├── round1/                       # Results, logs, PnL charts
│   ├── ROUND1/                   # Historical market data (days -2, -1, 0)
│   ├── img.png … img5.png        # PnL charts per submission
│   └── *.json / *.log            # Raw submission results
│
├── analysis/                     # Research & diagnostic scripts
├── docs/                         # Strategy docs & notes
├── tests/                        # Local backtesting
└── find_pepper_fv.py             # Pepper fair value diagnostic
```

---

## 🤖 v4 Algorithm — Full Breakdown

### Products Traded

| Product | Character | Strategy |
|---------|-----------|----------|
| `ASH_COATED_OSMIUM` | Stable, mean-reverting around 10,000 | Dual-mode: TAKE mispricings + MAKE spread |
| `INTARIAN_PEPPER_ROOT` | Trending upward +500 XIRECS/day | EMA trend-following with buy-side bias |

---

### Key Insight — Pepper Is NOT Like Emeralds

Running `find_pepper_fv.py` on all three days of historical data revealed:

| Day | Min | Median | Max | Intraday Drift |
|-----|----:|-------:|----:|---------------:|
| −2 | 9,998 | 10,500 | 11,003 | **+500** ⚠️ |
| −1 | 10,995 | 11,500 | 12,006 | **+500** ⚠️ |
| 0 | 11,994 | 12,500 | 13,007 | **+500** ⚠️ |
| 1 *(live)* | ~12,994 | **~13,500** | ~14,007 | +500 extrapolated |

Pepper rises exactly **+500 XIRECS every day** in a perfectly linear trend. A fixed fair value (as used in v1–v3) always fights the trend — bots have directional information and trade against us, causing adverse selection losses. The fix is to **track the price with EMA** and hold long.

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
"soft_limit":     50       # position cap (±50 out of ±80 limit)
"take_width":     2        # take orders ≥2 away from FV
"make_width":     3        # passive quote offset
"order_size":     12
"use_ema":        False    # no EMA needed; FV is fixed
"trend_bias":     0.0      # no directional bias
```

**How it earns:**
- Takes any ask below 9,998 or any bid above 10,002 immediately (TAKE phase)
- Posts passive bid ~9,997 and ask ~10,003 inside the spread (MAKE phase)
- Bots fill these passive orders frequently → earns ~1–2 XIRECS per round-trip
- Inventory skew adjusts quotes when position drifts (avoids one-sided exposure)
- **Result: +1,404 XIRECS** — never went negative throughout the day

**Critical fix (v4a → v4b):**

```python
# BROKEN (v4a) — quotes sat at the outer edge, bots ignored them
our_bid = min(our_bid, best_bid)    # edge of spread
our_ask = max(our_ask, best_ask)    # edge of spread

# FIXED (v4b) — quotes sit inside the spread, bots fill us
our_bid = min(our_bid, best_ask - 1)   # inside spread
our_ask = max(our_ask, best_bid + 1)   # inside spread
```

---

### INTARIAN_PEPPER_ROOT — EMA Trend Following

**Fair value:** Dynamic EMA tracking the upward drift.  
**Seed value:** `13,500` (extrapolated Day 1 start from linear trend).

**Configuration:**
```python
"fair_value":     13_500
"soft_limit":     40       # conservative cap for a trending asset
"take_width":     3        # wider (avg spread ~14 ticks)
"make_width":     6        # wide passive quotes around EMA
"order_size":     8
"use_ema":        True     # EMA adapts to price movement each tick
"ema_alpha":      0.10     # fast adaptation (tracks trend quickly)
"trend_bias":     0.5      # shifts adj_fv UP → prefer buying
```

**How it earns:**
- EMA starts at 13,500 and updates every tick: `EMA = 0.10 × mid + 0.90 × EMA`
- `trend_bias = 0.5` shifts the effective FV up by `0.5 × make_width = 3 points`
  - This makes our bid more aggressive (buys earlier) and our ask more conservative (sells later)
- The algorithm accumulates Pepper long as price rises → mark-to-market gain
- **Final position: +40 units** (maxed soft limit), rode the entire uptrend

**EMA + trend_bias formula:**
```
adj_fv = EMA + imbalance_signal × (make_width × 0.5)
adj_fv = adj_fv + trend_bias × make_width

our_bid = adj_fv − make_width + inventory_skew
our_ask = adj_fv + make_width + inventory_skew
```

- **Result: +3,696 XIRECS** — grew linearly all day, perfectly tracking the trend

---

### Order Book Imbalance Signal

Applied to both products. Measures buy vs sell pressure at the top of the book:

```python
imbalance = (bid_vol − ask_vol) / (bid_vol + ask_vol)   # range [-1, +1]
```

Smoothed over 20 ticks and used to nudge `adj_fv`:
- `imbalance > 0` (more buyers) → raise adj_fv slightly → our quotes shift up
- `imbalance < 0` (more sellers) → lower adj_fv → our quotes shift down

This reduces adverse selection by aligning our quotes with short-term order-flow pressure.

---

### State Persistence (AWS Lambda Stateless)

The platform runs each `run()` call as a stateless AWS Lambda invocation.  
All state is serialized into the `traderData` string and restored each tick:

```python
class SerializableState:
    ema_fv: Dict[str, float]          # EMA fair value per product
    price_history: Dict[str, List]    # recent prices for momentum
    imbalance_history: Dict[str, List] # smoothed imbalance signal
    last_timestamp: int               # detects day resets
```

On a day reset (`timestamp < last_timestamp`), short-term histories are cleared but EMA estimates are preserved.

---

## 🚀 Quick Start

```bash
# Submit this file to the Prosperity platform
algorithms/round1_trader_v4.py

# Re-run the Pepper fair value diagnostic
python3 find_pepper_fv.py

# Run local tests
python3 tests/test_v2.py    # baseline
python3 tests/test_v3.py    # conservative Pepper
```

---

**Last Updated:** April 2026  
**Best Version:** v4b (`algorithms/round1_trader_v4.py`)  
**Expected PnL:** ~+5,100 XIRECS 🏆
