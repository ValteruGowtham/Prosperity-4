# Prosperity 4 - Algorithmic Trading Bot

## Version 2.0: Conservative Mean-Reversion Market Maker

### Overview

This trading bot implements a **conservative mean-reversion market-making strategy** designed for the Prosperity trading competition. The algorithm passively places bid and ask orders around an estimated fair value, profiting from the bid-ask spread while managing inventory risk and avoiding large drawdowns.

---

## Version History

### v2.0 (Current) - Conservative Mean-Reversion Market Maker
Major rewrite addressing severe drawdown issues found in v1.0:
- **Passive market making**: Earn the spread instead of paying it
- **Momentum filter**: Avoid trading against strong price trends
- **Minimum deviation threshold**: Only trade when price meaningfully deviates from fair value
- **Reduced position sizing**: Smaller orders and tighter position limits
- **Volatility-adjusted spreads**: Wider spreads in volatile conditions
- **Per-product `ProductTracker`**: Clean state management with price history, fair value, and momentum tracking

### v1.0 - Mean-Reversion Market Maker
- Rolling median fair value estimation
- Volatility-adjusted spread sizing
- Inventory-based quote skewing
- Conservative position limits
- Backtested on historical data

---

## Strategy Approach

### Core Philosophy

**Version 2.0** uses a **conservative passive market-making** approach focused on earning the spread rather than aggressively taking liquidity:

1. **Earn, don't pay**: Place passive limit orders inside the spread — never cross the market by buying at the ask or selling at the bid
2. **Trade with conviction**: Only place aggressive orders when price deviation from fair value exceeds a minimum threshold
3. **Respect momentum**: Don't fight strong directional price moves — if price is crashing, don't catch the falling knife
4. **Limit risk**: Smaller order sizes and tighter position limits to control drawdowns

### Key Insights from Data Analysis

#### EMERALDS
- **Extremely stable**: Trades in a tight range around 10,000 (±4 points)
- **Mid price range**: 9,996 - 10,004
- **Average spread**: ~15.74 points
- **Low volatility**: Predictable mean-reverting behavior
- **Trade frequency**: 399 trades over the dataset

#### TOMATOES
- **More volatile**: Trades around 4,993 with wider swings
- **Mid price range**: 4,946 - 5,036 (90-point range!)
- **Average spread**: ~13.02 points
- **Higher opportunity**: More deviation from mean = more trading signals
- **Trade frequency**: 820 trades over the dataset

---

## Strategy Components

### 1. Fair Value Estimation
- **Method**: Rolling median of recent mid-prices
- **Window**: 15 most recent price observations (reduced from 20 for faster adaptation)
- **Why median?**: More robust to outliers than mean
- **Fallback**: Uses known fundamental values (10,000 for EMERALDS, 5,000 for TOMATOES)

```
Fair Value = Median(last 15 mid-prices)
```

### 2. Passive Market Making (Key v2.0 Change)

Instead of aggressively taking liquidity at the best bid/ask, we place **passive limit orders** inside the spread:

```
Base Half-Spread = 5.0 (both products, reduced from v1)

Optimal Bid = Fair Value - Adjusted Half-Spread + Inventory Skew
Optimal Ask = Fair Value + Adjusted Half-Spread + Inventory Skew
```

These orders sit **between** the best bid and best ask, earning the spread when they get filled. We only cross the spread when price deviation exceeds our minimum threshold.

### 3. Minimum Deviation Threshold

Only place aggressive orders (closer to mid price) when the deviation is meaningful:

| Product | Min Deviation | Rationale |
|---------|--------------|-----------|
| EMERALDS | 0.08% | Low volatility, small moves are noise |
| TOMATOES | 0.12% | Higher volatility, needs larger signal |

```python
if abs_deviation >= min_deviation and momentum_supports_direction:
    # Move orders closer to mid price for faster fill
    aggressive_bid = Fair Value - Adjusted Spread × 0.5
```

### 4. Momentum Filter (New in v2.0)

Tracks price direction over the last 5 ticks to avoid trading against trends:

```
Momentum = Avg(recent prices second half) - Avg(recent prices first half)
```

**Decision rules:**
- Price below fair value (want to buy) + momentum strongly negative (falling) → **skip trade**
- Price above fair value (want to sell) + momentum strongly positive (rising) → **skip trade**
- All other cases → trade normally

This prevents "catching falling knives" and reduces large drawdowns.

### 5. Volatility Adjustment
- **Purpose**: Widen spreads during volatile periods to protect against adverse selection
- **Method**: Scale spread based on absolute deviation from fair value
- **Formula**:
  ```
  Vol Multiplier = 1.0 + (|Deviation| × 100)
  Adjusted Spread = Base Spread × Vol Multiplier
  ```

### 6. Inventory Management
- **Purpose**: Prevent accumulating too large a position in one direction
- **Mechanism**: Skew quotes based on current inventory
  - **Long position**: Lower bids/asks to encourage selling
  - **Short position**: Raise bids/asks to encourage buying
- **Position limits** (reduced in v2.0):

| Product | v1.0 Limit | v2.0 Limit | Change |
|---------|-----------|-----------|--------|
| EMERALDS | ±30 | **±20** | -33% |
| TOMATOES | ±25 | **±15** | -40% |

- **Skew factor**: Reduced from 0.5 → **0.3** (less aggressive position reduction)

```
Inventory Skew = (Current Position / Max Position) × 0.3 × Spread
```

### 7. Order Sizing (Reduced in v2.0)

| Product | v1.0 Order Size | v2.0 Order Size | Change |
|---------|----------------|----------------|--------|
| EMERALDS | 8 | **5** | -37% |
| TOMATOES | 5 | **3** | -40% |

Smaller orders mean smaller losses on any single wrong trade.

---

## Configuration

```python
PRODUCT_CONFIG = {
    "EMERALDS": {
        "fair_value_default": 10000,
        "target_half_spread": 5,          # Tighter spread
        "order_size": 5,                   # Reduced from 8
        "max_position": 20,               # Reduced from 30
        "min_deviation_pct": 0.0008,      # 0.08% threshold
        "fair_value_window": 15,           # Faster adaptation
    },
    "TOMATOES": {
        "fair_value_default": 5000,
        "target_half_spread": 5,           # Tighter spread
        "order_size": 3,                   # Reduced from 5
        "max_position": 15,               # Reduced from 25
        "min_deviation_pct": 0.0012,      # 0.12% threshold (higher for volatility)
        "fair_value_window": 15,
    },
}

# Global settings
INVENTORY_SKEW_FACTOR = 0.3        # Reduced from 0.5
MOMENTUM_WINDOW = 5                # Look back 5 ticks
MOMENTUM_THRESHOLD = 0.0003        # Skip trades against strong momentum
```

---

## Architecture

### File Structure

```
Prosperity 4/
├── trader.py                   # Main trading algorithm (v2.0)
├── trading_bot.py              # Legacy backtesting code (v1.0)
├── README.md                   # This file
└── TUTORIAL_ROUND_1/           # Historical market data
    ├── prices_round_0_day_-1.csv
    ├── prices_round_0_day_-2.csv
    ├── trades_round_0_day_-1.csv
    └── trades_round_0_day_-2.csv
```

### Core Classes

| Class | Purpose |
|-------|---------|
| `Trader` | Main entry point — `run()` method called by platform |
| `ProductTracker` | Per-product state: price history, fair value, momentum, volatility |
| `Order` | Order representation matching platform's datamodel |
| `OrderDepth` | Buy/sell order book representation |
| `TradingState` | Full market state snapshot |

### Data Flow

```
TradingState (from platform)
        ↓
    Trader.run()
        ↓
  For each product:
        ↓
  ProductTracker.update(mid_price)
        ↓
  ┌───────┼──────────────────────┐
  ↓       ↓                      ↓
Fair Value  Momentum        Volatility
  ↓       ↓                      ↓
  Calculate Optimal Bid/Ask with all adjustments
        ↓
  ┌─────┴──────────────────────┐
  ↓                            ↓
Passive Orders             Aggressive Orders
(inside spread, earn)      (if deviation > threshold)
        ↓
  Return [Order, ...] per product
```

---

## What Changed from v1.0 → v2.0

### v1.0 Problems (identified from performance graph)
1. **Massive drawdowns** (~-500 PNL): Strategy was aggressively taking liquidity, paying the spread
2. **Slow recovery**: Took ~170K iterations to recover from losses
3. **High volatility**: PNL extremely jagged — trading too frequently with too much size
4. **Barely profitable**: After all the risk, final PNL was only ~+120

### v2.0 Fixes

| Problem | v1.0 Behavior | v2.0 Fix |
|---------|--------------|----------|
| Paying spread | Bought at best ask, sold at best bid | Passive orders inside spread |
| No conviction | Traded every tick | Min deviation threshold |
| Fighting trends | No momentum check | Momentum filter blocks counter-trend trades |
| Large drawdowns | Order size 5-8, max pos 25-30 | Order size 3-5, max pos 15-20 |
| Noise trading | No threshold | 0.08%-0.12% deviation required |

### Expected Improvement
- **Smoother PNL curve**: Fewer losing trades, smaller losses per trade
- **Smaller drawdowns**: Momentum filter prevents catching falling knives
- **Better risk-adjusted returns**: Same or better total profit with much less risk
- **Faster recovery**: Smaller positions mean faster recovery from any drawdown

---

## How to Run

### Requirements
- Python 3.10+
- No external dependencies (pure standard library)

### Test Locally
```bash
python3 -c "from trader import Trader; print('OK')"
```

### Submit to Platform
Upload `trader.py` — the platform will call `Trader().run(state)` each iteration.

---

## Future Improvements (v3.0+)

### Planned Enhancements

1. **Pair Trading Strategy**
   - Exploit price relationships between products
   - Statistical arbitrage when spread deviates from normal

2. **Order Book Dynamics**
   - Analyze order flow imbalances
   - Detect market maker vs taker activity
   - Predict short-term price movements from book pressure

3. **Adaptive Parameters**
   - Dynamic spread sizing based on time of day
   - Position limits that adjust to market conditions
   - Machine learning for fair value estimation

4. **Execution Optimization**
   - Smart order routing (when to use limit vs market orders)
   - Order sizing based on available liquidity
   - Iceberg orders for large positions

5. **Risk Management**
   - Stop-loss mechanisms
   - Drawdown limits
   - Correlation-based portfolio risk

6. **Performance Metrics**
   - Sharpe ratio calculation
   - Maximum drawdown tracking
   - Profit attribution by signal type

---

## Development Workflow

When iterating on the strategy:

1. **Modify** `trader.py` (strategy logic in `Trader.run()`)
2. **Test** by importing and running with mock `TradingState`
3. **Upload** to Prosperity platform for simulation
4. **Analyze** the PNL graph and log files
5. **Compare** performance across versions
6. **Document** changes in this README under "Version History"

---

## Contact & Support

For questions about the strategy or to collaborate on improvements, reach out to the team.

---

**Disclaimer**: This is a competition trading bot. Past performance does not guarantee future results. Always test thoroughly before deploying.
