# Prosperity 4 — Round 1 Trading Algorithm

## 🏆 Final Submission: `round1_trader_v6.py`

> **Local test score: ~8,288 XIRECS** (hard ceiling — see why below)
> **Live Day 1 projected: ~76,000 XIRECS** 🚀

---

## 📈 Full Version History

| Version | File | Osmium | Pepper | **Total** | Notes |
|---------|------|-------:|-------:|----------:|-------|
| v1 | `algorithms/round1_trader.py` | +1,296 | −1,692 | **−395** ❌ | Mean-reversion only — Pepper not trending |
| v2 | `algorithms/round1_trader_v2.py` | +1,296 | 0 | **+1,296** ✅ | Disabled Pepper entirely |
| v3 | `algorithms/round1_trader_v3.py` | +1,297 | −556 | **+741** ⚠️ | Conservative re-entry, still wrong direction |
| v4a | `algorithms/round1_trader_v4.py` | +430 | +3,656 | **+4,086** | EMA introduced; Osmium inside-spread bug |
| v4b | `algorithms/round1_trader_v4.py` | +1,404 | +3,696 | **+5,100** | Fixed Osmium clamping |
| v5c | `round1_trader_v5.py` | +1,348 | +6,837 | **+8,285** | Long-only Pepper; EMA bug fixed |
| **v6** ⭐ | `round1_trader_v6.py` | **+1,452** | **+6,837** | **~8,288** | Seed fix + Osmium improvements |

> **Why do v5c and v6 show the same local score?**
> The local backtester runs **only on Day 0 historical data**, where Pepper moves just **+101 points** (11,998 → 12,099). This creates an absolute ceiling of `75 × 101 - ~740 friction ≈ 6,836` Pepper PnL. No algorithm can exceed ~8,300 locally. The v6 fixes only matter on the **live server (Day 1)**.

---

## 🔑 The Critical Difference: v6 is built for the Live Round

### v5c would earn ZERO on Pepper in the live round

TAKE phase fires when: `ask ≤ EMA − take_width`

| | Day 0 (local test) | Day 1 (live server) |
|---|---|---|
| Opening ask | ~12,006 | ~~13,014~~ |
| v5c threshold (seed=13,000) | 12,999 → **fires ✅** | 12,999 → **DEAD ❌** |
| v6 threshold (seed=14,500) | 14,499 → **fires ✅** | 14,499 → **fires ✅** |

With `seed=13,000`, the Day 1 opening ask of 13,014 is **above** the threshold of 12,999. TAKE never fires. Pepper earns 0 XIRECs for the entire live round.

With `seed=14,500`, threshold is 14,499. Day 1 ask of 13,014 **fires immediately**. Bot fills +75 in the first 2 ticks and holds all day while price rises ~+1,000 points.

---

## 🛠️ v6 Changes vs v5c

| Parameter | v5c | **v6** | Impact |
|---|---|---|---|
| `PEPPER_SEED` | 13,000 | **14,500** | 🔑 Pepper fires from tick 1 on live server → +~67,000 XR |
| Osmium `take_width` | 2 | **1** | Captures asks ≤9,999 (~+700 XR) |
| Osmium `soft_limit` | 60 | **75** | 25% more capacity (~+200 XR) |
| Pepper `ema_alpha` | 0.15 | **0.10** | Keeps EMA above asks longer (~+50 XR) |

**Rule going forward:** Always set `PEPPER_SEED = expected END-of-day price`, not start price. The seed must sit comfortably above the opening ask so TAKE fires from tick 1.

---

## 📁 Project Structure

```
Prosperity 4/
│
├── round1_trader_v6.py           ← ⭐ FINAL SUBMISSION (submit this)
├── round1_trader_v5.py           ← Previous best (v5c, kept for reference)
│
├── algorithms/                   ← Full algorithm history
│   ├── round1_trader.py          # v1
│   ├── round1_trader_v2.py       # v2
│   ├── round1_trader_v3.py       # v3
│   ├── round1_trader_v4.py       # v4
│   ├── round1_trader_v5.py       # v5c
│   └── round1_trader_v6.py       # v6 ← mirror of root
│
├── round1/                       ← All submission results
│   ├── ROUND1/                   # Historical market data (Day -2, -1, 0)
│   ├── img.png … img9_v6.png     # PnL charts per submission
│   ├── 256780_v5c.json/.log      # v5c result logs
│   └── 260595_v6.json/.log       # v6 result logs
│
├── analysis/                     # Research & diagnostic scripts
├── docs/                         # Strategy notes
├── tests/                        # Local backtesting
└── README.md
```

---

## 🤖 Algorithm Design — v6

### Products Traded

| Product | Character | Strategy |
|---------|-----------|----------|
| `ASH_COATED_OSMIUM` | Stable, mean-reverting around 10,000 | Market making: TAKE mispricings + MAKE passive spread |
| `INTARIAN_PEPPER_ROOT` | Trending upward ~+1,000 XR/day | Long-only EMA trend-following |

---

### Architecture — Dual-Phase Execution

```
Phase 1 — TAKE (executes first)
  ask ≤ EMA − take_width  →  BUY immediately (lock in guaranteed profit)
  bid ≥ EMA + take_width  →  SELL immediately (Osmium only)

Phase 2 — MAKE (passive quoting)
  Post limit orders around EMA, clamped INSIDE the spread
  Inventory skew lowers bid when long, raises ask when long
  (mean-reverts position automatically)
```

---

### ASH_COATED_OSMIUM Configuration

```python
"fair_value"  : 10_000   # Confirmed stable across all data days
"soft_limit"  : 75       # v6: raised from 60, 25% more round-trip capacity
"take_width"  : 1        # v6: lowered from 2, captures asks ≤9,999
"make_width"  : 3        # 6 ticks per round-trip (bid@9,997 / ask@10,003)
"order_size"  : 12
"use_ema"     : False
"long_only"   : False
```

### INTARIAN_PEPPER_ROOT Configuration

```python
"fair_value"  : 14_500   # ← THE KEY FIX. End-of-day seed >> opening ask
"soft_limit"  : 75       # Hold max long position all day
"take_width"  : 1        # buy any ask below EMA − 1
"make_width"  : 5        # passive bids around EMA
"order_size"  : 30       # fills +75 in 2-3 ticks
"use_ema"     : True
"ema_alpha"   : 0.10     # v6: slowed from 0.15, keeps EMA above asks longer
"long_only"   : True     # NEVER place ask orders — hold the full position
```

---

## 📊 Live Day 1 Projection

| Component | Projected PnL |
|---|---|
| Pepper (75 units × ~+1,000 drift) | ~73,000–75,000 XR |
| Osmium (spread capture) | ~1,500–2,500 XR |
| **Total expected** | **~74,500–77,500 XR** |

---

## 🚀 Submission

```bash
# Submit this file to the Prosperity platform
round1_trader_v6.py
```

---

**Last Updated:** April 2026 | **Final Version:** v6 | **Submitted:** `round1_trader_v6.py`
