# Prosperity 4 - Round 1 Algorithm v2.0

## 🎯 Performance Improvement: **-395 → +1,296 XIRECS**

---

## 📊 v1.0 vs v2.0 Comparison

| Metric | v1.0 | v2.0 | Change |
|--------|------|------|--------|
| **ASH_COATED_OSMIUM** | +1,296.56 | +1,296.56 | ✅ Same |
| **INTARIAN_PEPPER_ROOT** | **-1,692.00** | **0.00** | ✅ Eliminated loss |
| **Net PnL** | **-395.44** | **~+1,296.56** | **🚀 +1,692 improvement** |

---

## 🔍 Root Cause Analysis (v1.0 Failure)

### What Went Wrong:

**INTARIAN_PEPPER_ROOT: -1,692 XIRECS loss**

1. **Strategy Bug**: Algorithm was SHORT-biased (mean-reversion)
2. **Market Reality**: Price trended UP continuously (12,000 → 12,100)
3. **Position Buildup**: Accumulated -40 short position and held it
4. **Mark-to-Market Losses**: -17 XIRECS per point of upward price movement

### Evidence from Logs:

```
Position Inference:
  t=0-49900  | Price: +51.0  | PnL: -368.6  | Position: SHORT ❌
  t=50000-99900 | Price: +56.5 | PnL: -1322.0 | Position: SHORT ❌

PnL Events:
  890 negative changes vs 8 positive changes
  Late game: -4.00 PnL per tick (holding max short position)
```

### The Fatal Pattern:

```
Our Algorithm: "Price is high → SELL (mean-reversion)"
Market Reality: "Price keeps going higher → never mean-reverts"
Result: Short position accumulates losses as price trends up
```

---

## ✅ v2.0 Fix

### Simple Solution: **Skip INTARIAN_PEPPER_ROOT Entirely**

**Rationale:**
- ASH_COATED_OSMIUM strategy works perfectly (+1,296 XIRECS)
- Pepper strategy is fundamentally broken (trend-fighting)
- Better to earn +1,296 than lose -395
- Can revisit Pepper with proper trend-following strategy later

### Code Changes:

```python
# v1.0: Traded both products
PRODUCT_CONFIG = {
    "ASH_COATED_OSMIUM": {...},
    "INTARIAN_PEPPER_ROOT": {...},  # ❌ Caused -1692 loss
}

# v2.0: Only trade Osmium
PRODUCT_CONFIG = {
    "ASH_COATED_OSMIUM": {...},  # ✅ Works perfectly
    # Pepper disabled - skip until proper strategy implemented
}

# In run() method:
for product in state.order_depths:
    if product not in PRODUCT_CONFIG:
        result[product] = []  # Skip unknown products
        continue
```

---

## 📈 Expected Performance (v2.0)

### Conservative Estimate:
- **ASH_COATED_OSMIUM**: +1,296 XIRECS (proven from v1.0)
- **INTARIAN_PEPPER_ROOT**: 0 XIRECS (no trading)
- **Net PnL**: **+1,296 XIRECS**

### PnL Curve Prediction:
```
v1.0: Rise to +430 → Crash to -395 ❌
v2.0: Steady rise to +1,296 ✅
```

---

## 🎯 Future Improvements (v3.0+)

### Option 1: Trend-Following for Pepper
```python
# Only go LONG in uptrends
if momentum > threshold:
    place_buy_orders()
else:
    skip_trading()
```

### Option 2: Conservative Market Making
```python
# Very tight position limits
max_position = 5  # Instead of 40
# Quick exit from positions
# Wide spreads to avoid adverse selection
```

### Option 3: Statistical Arbitrage
```python
# If Osmium and Pepper are correlated
# Use Osmium moves to predict Pepper direction
```

---

## 📁 File Structure

```
Prosperity 4/
├── round1_trader.py           # v1.0 - Original (DO NOT USE)
├── round1_trader_v2.py        # v2.0 - Fixed version ✅
├── test_v2.py                 # Tests for v2.0
├── analyze_performance.py     # Performance analysis script
├── deep_analysis.py           # Deep dive into trading activity
├── final_diagnosis.py         # Root cause diagnosis
├── ROUND1_README.md           # Original strategy documentation
└── PERFORMANCE_ANALYSIS.md    # v1.0 performance breakdown
```

---

## 🚀 How to Submit

1. **Upload**: `round1_trader_v2.py` to Prosperity platform
2. **Expected Result**: +1,296 XIRECS (vs -395 in v1.0)
3. **Risk**: Low (only trades proven profitable product)

---

## 📝 Key Learnings

1. **Test thoroughly before live trading** - v1.0 Pepper strategy was never validated
2. **Monitor position direction** - being short in uptrend is deadly
3. **Simple is better** - skipping bad trades beats complex bad strategies
4. **Data analysis is crucial** - logs revealed the exact problem
5. **Iterate fast** - v1.0 → v2.0 in one analysis session

---

**Version**: 2.0
**Status**: Ready for submission ✅
**Expected PnL**: +1,296 XIRECS
**Improvement**: +1,692 XIRECS vs v1.0
