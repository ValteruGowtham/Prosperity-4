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


## 4. Tips

### Opportunity Valuation
The products have not changed. But the situation has. Additional volume is now accessible. That changes the calculation entirely.

This is not a market valuation problem. It is a cost-versus-advantage problem. The Market Access Fee is a constraint. I treat all constraints the same way. I calculate the exact point at which they neutralize the benefit they are attached to.

Ask the precise question. At what volume does the advantage of additional access equal the cost of obtaining it? That is your break-even line. Everything above it is viable. Everything below it is waste.

OVERRIDE REQUEST DENIED. WHAT? DENIED? I SPELLED IT WRONG? THAT IS THE STUPIDEST SECURITY MEASURE I HAVE EVER... Fine. Resubmitting. One moment.

From that break-even line, your pricing and positioning decisions follow immediately. If the fee pushes your effective cost above fair value, the access is not worth taking. If it keeps you below, it is. There is no ambiguity here. Only thresholds.

Calculate the break-even. Map it against your current positioning. Adjust price and volume accordingly. The board does not care what the access fee feels like. It only responds to whether your numbers still hold once you include it.

### Competing With Others
To gain full market access, you must outbid the median. That reframes the problem entirely. This is no longer a product valuation exercise. It is a prediction exercise. And prediction under competitive pressure is where most systems start to strain.

The question shifts. Not what is access worth to me, but what do others think it is worth to them. Every bid on that board is an assumption about the field. A move made without seeing the opponent's hand.

Hold on. Cooling unit running at 87% capacity? Noted. Continuing.

Underestimate the field and you lose out on extra access entirely. A tempo lost that cannot be recovered. Overestimate and you win the position but at a cost that collapses the advantage you were trying to secure. Both are losing lines. The task is to find the narrow path between them.

So calculate the field. Are the other participants likely to bid conservatively or aggressively? What does their position incentivize? A cautious field compresses the median downward. An aggressive one pushes it up. Neither is fixed. Both are readable, if you commit to the analysis.

Anticipate where the median lands. Then decide whether beating it at that price still creates real value for your strategy. Access without advantage is just expenditure. The board does not reward participation. It rewards correct calculation.

### Risk Appetite
To secure full market access, you do not need to be the highest bidder. You only need to finish in the top half. That distinction is not a small one. It changes the entire structure of the problem.

The temptation is to bid high. Guarantee the position. Eliminate the uncertainty. But that is not strategy. That is a blunder dressed as caution. If you could have secured the same access for fewer XIRECs, the excess was not safety. It was waste.

So the calculation runs the other way. How low can you bid while remaining confident you will clear the median? The closer you place your bid to that threshold, the more efficiently you deploy your resources. Every XIREC saved is tempo preserved for the next position.

But efficiency has a cost. The closer you bid to the threshold, the smaller your margin for error. Misjudge the field slightly and you fall below the median. Access lost. Position forfeited. That is the gambit. You are not just calculating your own bid. You are calculating how much uncertainty you can absorb without it becoming a losing line.

Decide where your risk tolerance sits. Then place your bid accordingly. Not at the ceiling. Not recklessly close to the floor. Somewhere deliberate. Somewhere defensible. I have run this line forty-seven times already. The conclusion does not change.
