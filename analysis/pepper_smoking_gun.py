"""
Deep Dive: Adverse Selection Pattern in Pepper
Understanding WHY bots are trading against us 99.4% of the time
"""

import json
import csv
from io import StringIO
import statistics

with open('round1/123540.json', 'r') as f:
    data = json.load(f)

reader = csv.DictReader(StringIO(data['activitiesLog']), delimiter=';')
rows = list(reader)

pepper_data = []
for row in rows:
    if row['product'] == 'INTARIAN_PEPPER_ROOT':
        pepper_data.append({
            'timestamp': int(row['timestamp']),
            'mid_price': float(row['mid_price']),
            'bid_price_1': float(row['bid_price_1']) if row['bid_price_1'] else None,
            'ask_price_1': float(row['ask_price_1']) if row['ask_price_1'] else None,
            'bid_volume_1': int(row['bid_volume_1']) if row['bid_volume_1'] else None,
            'ask_volume_1': int(row['ask_volume_1']) if row['ask_volume_1'] else None,
            'pnl': float(row['profit_and_loss']),
        })

print("="*80)
print("ADVERSE SELECTION DEEP DIVE")
print("="*80)

print("""
KEY FINDING: 99.4% adverse selection rate
This means: Almost EVERY time we trade, bots immediately trade against us.

Question: Are bots exploiting OUR orders, or are we making bad trades?
""")

# Analyze the exact pattern of losses
print("\n🔍 LOSS PATTERN ANALYSIS:")
print("-" * 80)

# The losses are suspiciously consistent: -69.3 per segment
# Let's verify this pattern
segment_losses = []
segment_size = len(pepper_data) // 10

for seg in range(10):
    start = seg * segment_size
    end = start + segment_size
    segment = pepper_data[start:end]
    
    if segment:
        pnl_change = segment[-1]['pnl'] - segment[0]['pnl']
        segment_losses.append(pnl_change)

print(f"\nLoss per segment (should be consistent if systematic):")
for i, loss in enumerate(segment_losses):
    print(f"  Segment {i+1}: {loss:+6.1f}")

print(f"\nStatistical analysis:")
print(f"  Mean loss per segment: {statistics.mean(segment_losses):.2f}")
print(f"  Std dev: {statistics.stdev(segment_losses):.2f}")
print(f"  Min loss: {min(segment_losses):.2f}")
print(f"  Max loss: {max(segment_losses):.2f}")

# Check if the loss rate is constant
if statistics.stdev(segment_losses) < 5:
    print(f"\n✅ VERY consistent loss rate - suggests systematic issue")
else:
    print(f"\n⚠️  Variable loss rate - suggests random losses")

# 2. Check our bid/ask placement vs market movement
print("\n" + "="*80)
print("ORDER PLACEMENT ANALYSIS")
print("="*80)

print("\nSample of our orders vs market movement:")
print("-" * 80)

# Look at samples where PnL changed
trade_samples = []
for i in range(1, len(pepper_data)):
    if abs(pepper_data[i]['pnl'] - pepper_data[i-1]['pnl']) > 0.3:
        trade_samples.append(i)

print(f"\nAnalyzing {len(trade_samples)} trade events:")

# For each trade, check what happened before and after
for idx in trade_samples[:20]:  # First 20 trades
    d = pepper_data[idx]
    d_before = pepper_data[max(0, idx-5)]
    d_after = pepper_data[min(len(pepper_data)-1, idx+5)]
    
    pnl_before = d_before['pnl']
    pnl_after = d_after['pnl']
    price_before = d_before['mid_price']
    price_after = d_after['mid_price']
    
    pnl_change = pnl_after - pnl_before
    price_change = price_after - price_before
    
    print(f"  t={d['timestamp']:6d} | PnL: {pnl_before:6.1f}→{pnl_after:6.1f} ({pnl_change:+5.1f}) | "
          f"Price: {price_before:7.1f}→{price_after:7.1f} ({price_change:+5.1f})")

# 3. Key question: Are we accumulating position?
print("\n" + "="*80)
print("POSITION ACCUMULATION CHECK")
print("="*80)

# If PnL is dropping but price is rising → we're SHORT
# If PnL is dropping and price is stable → we had bad trades but closed position

print("\nChecking PnL vs Price correlation over time:")
print("-" * 80)

# Calculate rolling correlation
window = 100
for i in range(window, len(pepper_data), window * 10):
    chunk = pepper_data[i-window:i]
    
    pnls = [d['pnl'] for d in chunk]
    prices = [d['mid_price'] for d in chunk]
    
    # Simple correlation
    mean_pnl = statistics.mean(pnls)
    mean_price = statistics.mean(prices)
    
    cov = sum((pnls[j] - mean_pnl) * (prices[j] - mean_price) for j in range(len(pnls))) / len(pnls)
    std_pnl = statistics.stdev(pnls)
    std_price = statistics.stdev(prices)
    
    if std_pnl > 0 and std_price > 0:
        correlation = cov / (std_pnl * std_price)
    else:
        correlation = 0
    
    # Negative correlation = SHORT position (lose when price rises)
    # Positive correlation = LONG position (gain when price rises)
    if correlation < -0.5:
        position = "SHORT ❌"
    elif correlation > 0.5:
        position = "LONG ✅"
    else:
        position = "FLAT/MIXED"
    
    print(f"  t={chunk[0]['timestamp']:6d}-{chunk[-1]['timestamp']:6d} | "
          f"Correlation: {correlation:+.3f} | Position: {position}")

# 4. The smoking gun: loss rate analysis
print("\n" + "="*80)
print("LOSS RATE ANALYSIS - THE SMOKING GUN")
print("="*80)

print("""
From the data:
- Segment 2-10 all lose exactly ~69.3 XIRECS
- This is TOO consistent to be random
- Suggests a FIXED loss mechanism

Possible explanations:
1. We hold a FIXED short position (e.g., -7 units)
2. Price rises ~10 points per segment
3. Loss = -7 × 10 = -70 per segment ✓

Let's verify this hypothesis:
""")

# Check if price rises ~10 points per segment
print("Price increase per segment:")
for seg in range(9):
    start_idx = seg * segment_size
    end_idx = (seg + 1) * segment_size
    
    price_start = pepper_data[start_idx]['mid_price']
    price_end = pepper_data[end_idx]['mid_price']
    price_increase = price_end - price_start
    
    print(f"  Segment {seg+1}→{seg+2}: Price +{price_increase:.1f}")

# If we're short 7 units and price rises 10 points:
print(f"\nIf position = -7 (SHORT):")
print(f"  Loss per 10-point rise = -7 × 10 = -70 XIRECS")
print(f"  Actual average loss per segment = {statistics.mean(segment_losses):.1f} XIRECS")
print(f"  Match? {'✅ YES!' if abs(statistics.mean(segment_losses) + 70) < 5 else '❌ NO'}")

# 5. FINAL CONCLUSION
print("\n" + "="*80)
print("FINAL CONCLUSION")
print("="*80)

print("""
THE SMOKING GUN:
- Pepper price rises ~10 points per segment (10K ticks)
- We accumulate SHORT position (likely -7 from our asymmetrical limits)
- Loss per segment = -7 × 10 = -70 XIRECS ✓
- Over 9 segments = -630 XIRECS (close to -556 actual)

WHY ARE WE SHORT?
Our "LONG bias" strategy has:
  max_long = 15
  max_short = 7 (half of long)

But market making means:
  - We place both buy and sell orders
  - Bots trade against our SELL orders (we go short)
  - Bots DON'T trade against our BUY orders (we don't go long)
  - Result: Net SHORT position accumulation

WHY DON'T BOTS BUY FROM US?
- Bots know price will rise (they have information)
- They don't want to sell to us at current price
- They wait for higher prices to sell
- Meanwhile, they BUY from us (we sell short)

SOLUTION:
1. DON'T place sell orders at all (only buy)
2. Or use MUCH tighter short limit (±2 instead of ±7)
3. Or skip Pepper entirely (v2.0 strategy)

The issue is NOT spreads, NOT adverse selection, NOT volatility.
The issue is: WE KEEP GOING SHORT ON AN UPTRENDING ASSET!
""")
