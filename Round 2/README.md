# Prosperity 4 - Round 2 Strategy & Algorithm

This folder contains the Round 2 algorithm and related data analysis for the Prosperity 4 trading competition. Our primary submission is `algorithms/round2_v1.py`.

## 1. Algorithm Overview (`round2_v1.py`)

The Round 2 algorithm builds on the successes of Round 1, adapting perfectly to the new market dynamics observed in the Round 2 data. We trade two products: **ASH_COATED_OSMIUM** and **INTARIAN_PEPPER_ROOT**.

### ASH_COATED_OSMIUM (Market Making)
Our data analysis revealed key structural changes in Osmium for Round 2:
- **Price Drift:** The Fair Value (FV) is no longer anchored strictly at 10,000. It drifts slowly (e.g., averaging ~9,978 on Day 1).
- **Bot Behavior:** Trading bots constantly quote symmetrically around the true mid-price: `bid1 = mid - 8` and `ask1 = mid + 8` (spread of 16).

**Our Strategy:**
1. **Zero-Lag EMA:** We track FV using an Exponential Moving Average (EMA). Crucially, we seed the EMA using the *first observed mid-price* rather than a static 10,000. This eliminates the convergence lag that cost us fills in earlier versions.
2. **Aggressive Queue Priority:** We place passive quotes at `EMA - 3` (bid) and `EMA + 3` (ask). By quoting tighter than the bots (`±8`), we guarantee we are at the top of the order book (queue priority), capturing the bulk of the market orders.
3. **Safety Clamps & Inventory Skew:** We use inventory skew to adjust prices based on our current position to avoid hitting the limits. We also have safety clamps to ensure we never cross the spread or quote at unreasonable prices during fast market moves.

### INTARIAN_PEPPER_ROOT (Trend Riding)
The fundamental behavior of Pepper has not changed from Round 1:
- It maintains a perfectly linear upward trend of **+1,000 XIRECS per day**.
- Day 2 (Live Round) is expected to rise from 14,000 to 15,000.

**Our Strategy:**
1. **Aggressive Accumulation:** We initialize our EMA artificially high (`15,500`). This ensures our `TAKE` phase triggers on the very first tick, aggressively sweeping all available asks until we hit our soft limit of +75 units (usually within the first 6-7 ticks).
2. **Long-Only Hold:** Once filled, we simply hold the +75 position through the day, riding the +1000 trend for an easy ~75,000 PnL per day. We explicitly disable ask orders (`long_only = True`) so we never prematurely close the position.

---

## 2. The Tricky Part: Market Access Fee (Game Theory)

Round 2 introduces a **Market Access Fee**:
> *You may submit a fee via the `bid()` function. The top 50% of bidders win the auction and unlock an additional +25% trading volume. Crucially, teams outside the top 50% pay NOTHING.*

This is a brilliant game theory mechanic designed as a **first-price, top-50% auction with a safety net**. 

### Expected Value (EV) Analysis
What is +25% extra volume actually worth to our strategy?
- **Pepper:** Extra volume provides almost zero benefit. We hit our position limit of 75 in the first 6 ticks anyway, so having 25% more volume doesn't change our PnL.
- **Osmium:** Extra volume means more round-trips for our Market Making strategy. Based on backtests, our Osmium algorithm generates roughly ~4,600 PnL per day at base volume. A 25% increase in volume would generate an additional **~3,500 XIRECS** in profit over the 3-day round.

### Our Bidding Strategy: `2,500`
Since the extra volume is worth ~3,500 XIRECS to us, bidding anything above 3,500 guarantees we lose money *even if we win the auction*. 

We have set our bid to **2,500**.
- **Why it works:** It is highly likely to be in the top 50%. Many teams will ignore the mechanic, bid 0, or bid very low (e.g., 10 or 100). 
- **The Profit:** If we win the auction, we pay 2,500 but earn an estimated 3,500 from the extra volume, yielding a clean **+1,000 net profit**.
- **The Safety Net:** Because of the tournament rules, if 2,500 ends up in the bottom 50%, we simply lose the auction, **pay nothing**, and continue trading normally with our already highly-optimized baseline algorithm.

*Note: It is a zero-downside bet as long as our bid is lower than our expected return.*

---

## 3. Backtesting Note
When testing on the Prosperity platform, note that the sample data provided for the web backtester only covers the **first 100,000 timestamps** (10% of a full 1,000,000 tick day). 

If the backtester chart shows a final PnL of ~7,500, this is normal and expected. It represents exactly 10% of our full-day expected PnL (~75,000 from Pepper + ~4,600 from Osmium). The live run on the full day's data will scale up accordingly.
