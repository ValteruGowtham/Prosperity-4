# Prosperity 4 - Round 1 Trading Algorithm

## Products & Data Analysis

### ASH_COATED_OSMIUM
**Characteristics:**
- **Extremely stable**: Trades in tight range ~10000 ±20 points
- **Low volatility**: Standard deviation = 5.12 points
- **Strong mean reversion**: 69% mean reversion rate
- **Autocorrelation**: Decays quickly (lag-1: 0.74, lag-100: 0.57)
- **Average spread**: 16 points
- **Trade frequency**: ~425 trades/day, avg 2.3s between trades
- **Position limit**: 80

**Key Insight**: This product is HIGHLY mean-reverting. Prices oscillate around 10000 with very predictable patterns.

### INTARIAN_PEPPER_ROOT
**Characteristics:**
- **Strong upward trend**: Autocorrelation ~0.999 (nearly perfect)
- **Daily drift**: ~1000 points upward per day
- **Barely mean-reverting**: 51% rate (essentially random walk with drift)
- **Day-to-day variation**: Std of 1000 points in mean price
- **Average spread**: 12-14 points
- **Trade frequency**: ~335 trades/day, avg 2.9s between trades
- **Position limit**: 80

**Key Insight**: This product follows a strong upward trend. The autocorrelation of 0.999 means if it went up yesterday, it will go up today.

---

## Strategy Design

### Dual Strategy Approach

Given the completely different behaviors of these two products, we use different strategies:

| Product | Strategy | Rationale |
|---------|----------|-----------|
| ASH_COATED_OSMIUM | **Mean-Reversion Market Making** | Earn the spread in stable, oscillating market |
| INTARIAN_PEPPER_ROOT | **Trend Following** | Ride the upward trend with protective measures |

---

### Strategy 1: ASH_COATED_OSMIUM (Mean Reversion)

**Core Logic:**
1. Calculate EMA-based fair value (slow adaptation: α=0.05)
2. Place passive bid/ask orders around fair value
3. Tight spread targeting (half-spread = 4 points)
4. Large order sizes (10 units) due to stability
5. Conservative position limits (±40, half of max)

**Order Placement:**
```
Bid = Fair Value - 4 + Inventory Skew
Ask = Fair Value + 4 + Inventory Skew
```

**When to be aggressive:**
- Only when price deviates >0.03% from fair value
- AND momentum is not strongly against us
- Move orders closer to mid-price for faster fills

**Risk Management:**
- Momentum filter blocks trades during strong trends
- Inventory skew reduces exposure when position builds up
- Volatility adjustment widens spreads during unusual moves

---

### Strategy 2: INTARIAN_PEPPER_ROOT (Trend Following)

**Core Logic:**
1. Calculate EMA-based fair value (fast adaptation: α=0.2)
2. Track trend slope using linear regression
3. Project fair value forward based on trend
4. Blend: 70% EMA + 30% trend projection

**Trend Detection:**
```
Trend Slope = Linear regression slope of last 100 prices
Effective FV = Fair Value + (Slope × 10 ticks lookahead)
```

**Order Placement:**
```
Bid = Effective FV - 6 + Inventory Skew
Ask = Effective FV + 6 + Inventory Skew
```

**Trend-Adjusted Position Limits:**
- **Uptrend** (momentum > 0.05%):
  - Allow full long positions (±40)
  - Restrict short positions (±20)
- **Downtrend** (momentum < -0.05%):
  - Restrict long positions (±20)
  - Allow full short positions (±40)

**Why this works:**
- The 0.999 autocorrelation means trend continues
- By projecting forward, we stay ahead of the trend
- Wider spreads (6 vs 4) protect against adverse selection

---

## Configuration

```python
PRODUCT_CONFIG = {
    "ASH_COATED_OSMIUM": {
        "fair_value_default": 10000,
        "target_half_spread": 4,       # Tight
        "order_size": 10,              # Large (stable)
        "max_position": 40,            # Half of 80
        "min_deviation_pct": 0.0003,   # Very low
        "ema_alpha": 0.05,             # Slow
        "strategy": "mean_reversion",
    },
    "INTARIAN_PEPPER_ROOT": {
        "fair_value_default": 12000,
        "target_half_spread": 6,       # Wider
        "order_size": 8,               # Moderate
        "max_position": 40,            # Half of 80
        "min_deviation_pct": 0.001,    # Higher
        "ema_alpha": 0.2,              # Fast
        "strategy": "trend_following",
        "trend_window": 100,
    },
}
```

---

## State Management

**AWS Lambda is stateless** - all state must be serialized via `traderData`:

```python
class SerializableState:
    fair_value: Dict[str, float]          # EMA fair values
    price_history: Dict[str, List[float]] # For momentum/trend
    internal_position: Dict[str, int]     # Backup tracker
    trend_slope: Dict[str, float]         # For INTARIAN_PEPPER
    last_timestamp: int                   # Reset detection
```

State is serialized to JSON and passed between invocations.

---

## File Structure

```
Prosperity 4/
├── round1_trader.py           # Main trading algorithm
├── test_round1_trader.py      # Comprehensive tests
├── analyze_round1_data.py     # Initial data analysis
├── analyze_round1_corrected.py # Corrected statistical analysis
└── round1/ROUND1/             # Historical data
    ├── prices_round_1_day_-2.csv
    ├── prices_round_1_day_-1.csv
    ├── prices_round_1_day_0.csv
    ├── trades_round_1_day_-2.csv
    ├── trades_round_1_day_-1.csv
    └── trades_round_1_day_0.csv
```

---

## How to Run

### Test Locally
```bash
python3 test_round1_trader.py
```

### Submit to Platform
Upload `round1_trader.py` - the platform will call `Trader().run(state)` each iteration.

---

## Expected Performance

### ASH_COATED_OSMIUM
- High fill rate due to tight spreads
- Consistent profit from earning spread
- Low risk due to mean reversion
- Expected: Steady, low-volatility returns

### INTARIAN_PEPPER_ROOT
- Lower fill rate (wider spreads)
- Profits from trend alignment
- Higher risk during trend reversals
- Expected: Higher returns with more variance

---

## Risk Management

### Position Limits
- Internal limit: ±40 (half of 80 max)
- Additional trend-based adjustments for INTARIAN_PEPPER_ROOT

### Momentum Filter
- Blocks trades when momentum is strongly against position
- OSMIUM: Threshold 0.02% (very relaxed)
- PEPPER: Threshold 0.1% (more selective)

### Inventory Skew
- Adjusts quotes based on current position
- Factor: 0.3 × spread × (position / max_position)
- Prevents runaway position buildup

### Volatility Protection
- Widens spreads during unusual price moves
- OSMIUM: Multiplier = 1 + |deviation| × 20
- PEPPER: Multiplier = 1 + |deviation| × 30

---

## Key Differences from Tutorial Round

| Aspect | Tutorial (EMERALDS/TOMATOES) | Round 1 |
|--------|------------------------------|---------|
| Products | 2 stable products | 1 stable + 1 trending |
| Strategy | Uniform market making | Dual strategy |
| Fair Value | Pure EMA | EMA + trend projection |
| Position Limits | ±15-20 | ±40 |
| State Complexity | Moderate | Higher (trend tracking) |

---

## Future Improvements

1. **Adaptive Parameters**: Adjust spread/order size based on recent fill rate
2. **Trend Reversal Detection**: Catch when INTARIAN_PEPPER trend changes
3. **Cross-Product Signals**: Use OSMIUM moves to predict PEPPER (if correlated)
4. **Machine Learning**: Train model to predict short-term price movements
5. **Execution Optimization**: Dynamic order sizing based on liquidity

---

## Testing Checklist

- ✅ Import trader class
- ✅ Mean reversion strategy (ASH_COATED_OSMIUM)
- ✅ Trend following strategy (INTARIAN_PEPPER_ROOT)
- ✅ Position limits respected
- ✅ State persistence via traderData
- ✅ Order properties validation
- ✅ AWS Lambda reset simulation

---

**Algorithm Version**: 1.0 - Round 1 Initial
**Last Updated**: April 2026
**Status**: Ready for submission
