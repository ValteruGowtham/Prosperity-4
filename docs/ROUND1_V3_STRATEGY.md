# Round 1 Pepper Analysis & v3.0 Strategy

## 📊 Deep Analysis Results: INTARIAN_PEPPER_ROOT

### Key Findings:

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **Price Range** | 11995 - 12105 | 110 point range over day |
| **Std Deviation** | 29.00 | Very low volatility |
| **Mean Reversion** | 50.56% | Essentially random (no edge) |
| **Momentum Accuracy** | 15.03% | Momentum FAILS (inverse works!) |
| **Avg Spread** | 13.71 | Good for market making |
| **Trend** | +0.08% per 100 ticks | Slow steady upward drift |

### Price Behavior:

**10 Segments Analysis (each ~10K ticks):**
```
Segment 1: Mean 12005.4 | Trend +0.09%
Segment 2: Mean 12014.6 | Trend +0.10%
Segment 3: Mean 12024.7 | Trend +0.08%
...
Segment 10: Mean 12094.4 | Trend +0.07%
```

**Pattern**: Consistent upward drift of ~10 points per segment!

### What v1.0 Got Wrong:

```
v1.0 Strategy: Mean-reversion (SHORT bias)
  → Placed sells when price was high
  → Accumulated -40 short position
  → Price kept rising (+100 points)
  → Lost -1692 XIRECS

Reality: Price trends UP slowly
  → Should be LONG-biased or neutral
  → Market making works (spread=13.71)
  → Avoid directional bets
```

---

## ✅ v3.0 Strategy Design

### INTARIAN_PEPPER_ROOT: Conservative Market Making with LONG Bias

**Why This Works:**
1. **Steady upward drift** → LONG bias benefits from trend
2. **Low volatility** → Tight spreads profitable
3. **Wide spreads (13.71)** → Good profit per trade
4. **No mean reversion** → Don't fight the trend
5. **No momentum** → Don't chase direction

**Configuration:**
```python
"INTARIAN_PEPPER_ROOT": {
    "target_half_spread": 7,       # Wider than Osmium (4)
    "order_size": 5,               # Smaller (conservative)
    "max_position": 15,            # Tight limit (vs 40 in v1.0)
    "ema_alpha": 0.1,              # Moderate adaptation
    "long_bias": True,             # Key feature!
}
```

**LONG Bias Mechanism:**
- Max LONG: 15 units
- Max SHORT: 7 units (half of LONG)
- When short: More aggressive buying to cover
- When long: Normal market making

**Expected Behavior:**
- Accumulate small LONG positions over time
- Benefit from +0.08% drift per 100 ticks
- Earn spread on both sides
- Tight position limit prevents v1.0 disaster

---

## 📈 Expected Performance

### Conservative Estimate:

| Product | Strategy | Expected PnL |
|---------|----------|--------------|
| ASH_COATED_OSMIUM | Mean-reversion MM | +1,296 (proven) |
| INTARIAN_PEPPER_ROOT | Conservative MM + LONG bias | +200 to +500 |
| **Total** | **Both products** | **+1,496 to +1,796** |

### Risk Management:

**v1.0 Failure Mode:**
- Position limit: ±40
- Accumulated: -40 short
- Price rose: +100 points
- Loss: -40 × 100 = -4,000 (mark-to-market)

**v3.0 Protection:**
- Position limit: ±15 (LONG), ±7 (SHORT)
- Worst case: -7 short × 100 points = -700
- But LONG bias makes this unlikely
- Expected: Small LONG position benefits from drift

---

## 🔍 Strategy Comparison

| Version | Osmium | Pepper | Total | Status |
|---------|--------|--------|-------|--------|
| **v1.0** | +1,296 | -1,692 | -395 | ❌ Failed |
| **v2.0** | +1,296 | 0 | +1,296 | ✅ Good |
| **v3.0** | +1,296 | +200-500 | +1,496-1,796 | 🚀 Better! |

---

## 🎯 Key Learnings

### From v1.0 Failure:
1. **Never accumulate large positions in trending markets**
2. **Mean-reversion fails on trending products**
3. **Position limits are critical risk controls**
4. **Test strategies thoroughly before live trading**

### From Analysis:
1. **Pepper has steady upward drift** (not random)
2. **Low volatility = good for market making**
3. **Wide spreads = more profit per trade**
4. **LONG bias aligns with natural drift**

### For v3.0:
1. **Conservative position limits** (±15 vs ±40)
2. **LONG bias to benefit from drift**
3. **Wider spreads for safety**
4. **Smaller order sizes**

---

## 📁 Files Created

```
Prosperity 4/
├── round1_trader_v3.py       # v3.0 algorithm (both products) ✅
├── test_v3.py                 # Test suite for v3.0
├── analyze_pepper_deep.py     # Deep Pepper analysis
├── analyze_performance.py     # Performance analysis tools
├── round1_trader_v2.py        # v2.0 (Osmium only)
└── ROUND1_V3_STRATEGY.md      # This document
```

---

## 🚀 Next Steps

1. **Upload**: `round1_trader_v3.py` to Prosperity
2. **Monitor**: Watch Pepper PnL carefully
3. **Adjust**: If Pepper loses money, revert to v2.0
4. **Optimize**: Tune Pepper parameters based on results

**Goal**: Beat v2.0's +1,296 XIRECS with both products trading!

---

**Version**: 3.0
**Status**: Ready for testing ✅
**Expected**: +1,496 to +1,796 XIRECS
**Risk**: Low (tight position limits, conservative approach)
