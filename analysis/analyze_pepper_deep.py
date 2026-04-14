"""
Deep Analysis: INTARIAN_PEPPER_ROOT Price Behavior
Goal: Understand the true nature of Pepper to build a winning strategy
"""

import json
import csv
from io import StringIO
import statistics

# Load v2.0 results (only Osmium traded, Pepper data available)
with open('round1/121250.json', 'r') as f:
    data = json.load(f)

reader = csv.DictReader(StringIO(data['activitiesLog']), delimiter=';')
rows = list(reader)

# Extract Pepper data
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
        })

print("="*80)
print("INTARIAN_PEPPER_ROOT - DEEP BEHAVIORAL ANALYSIS")
print("="*80)

# Basic statistics
mid_prices = [d['mid_price'] for d in pepper_data if d['mid_price'] > 0]
timestamps = [d['timestamp'] for d in pepper_data if d['mid_price'] > 0]

print(f"\n📊 Basic Statistics:")
print(f"  Data points: {len(mid_prices)}")
print(f"  Time range: {timestamps[0]} - {timestamps[-1]}")
print(f"  Price range: {min(mid_prices):.1f} - {max(mid_prices):.1f}")
print(f"  Mean price: {statistics.mean(mid_prices):.2f}")
print(f"  Median price: {statistics.median(mid_prices):.2f}")
print(f"  Std dev: {statistics.stdev(mid_prices):.2f}")

# Price changes analysis
print(f"\n📈 Price Changes Analysis:")
price_changes = [mid_prices[i+1] - mid_prices[i] for i in range(len(mid_prices)-1)]
positive_changes = [c for c in price_changes if c > 0.01]
negative_changes = [c for c in price_changes if c < -0.01]
flat_changes = [c for c in price_changes if abs(c) <= 0.01]

print(f"  Total changes: {len(price_changes)}")
print(f"  Positive: {len(positive_changes)} ({len(positive_changes)/len(price_changes)*100:.1f}%)")
print(f"  Negative: {len(negative_changes)} ({len(negative_changes)/len(price_changes)*100:.1f}%)")
print(f"  Flat: {len(flat_changes)} ({len(flat_changes)/len(price_changes)*100:.1f}%)")
print(f"  Avg positive change: {statistics.mean(positive_changes):.2f}")
print(f"  Avg negative change: {statistics.mean(negative_changes):.2f}")

# Trend analysis - look at different time windows
print(f"\n🔍 Trend Analysis (Different Time Windows):")

for window_size in [100, 500]:
    trends = []
    for i in range(window_size, len(mid_prices)):
        window = mid_prices[i-window_size:i]
        start_price = window[0]
        end_price = window[-1]
        trend = (end_price - start_price) / start_price * 100
        trends.append(trend)
    
    if trends:
        avg_trend = statistics.mean(trends)
        positive_trends = len([t for t in trends if t > 0])
        
        print(f"  Window {window_size:5d} ticks: Avg trend {avg_trend:+6.3f}% | "
              f"Positive: {positive_trends}/{len(trends)} ({positive_trends/len(trends)*100:.1f}%)")

# Mean reversion analysis
print(f"\n🔄 Mean Reversion Analysis:")

# Check if price tends to revert to a moving average
window = 100
reversion_count = 0
total_opportunities = 0

for i in range(window, len(mid_prices) - 10):
    ma = statistics.mean(mid_prices[i-window:i])
    current = mid_prices[i]
    deviation = current - ma
    
    # If price is above MA, does it tend to go down?
    # If price is below MA, does it tend to go up?
    future_prices = mid_prices[i+1:i+11]
    future_avg = statistics.mean(future_prices)
    
    if deviation > 5:  # Significantly above MA
        total_opportunities += 1
        if future_avg < current:  # Price went down
            reversion_count += 1
    elif deviation < -5:  # Significantly below MA
        total_opportunities += 1
        if future_avg > current:  # Price went up
            reversion_count += 1

if total_opportunities > 0:
    reversion_rate = reversion_count / total_opportunities
    print(f"  Mean reversion rate: {reversion_rate:.2%}")
    if reversion_rate > 0.55:
        print(f"  ✅ Strong mean reversion detected!")
    elif reversion_rate > 0.5:
        print(f"  ⚠️  Weak mean reversion")
    else:
        print(f"  ❌ No mean reversion - trending behavior")

# Spread analysis
print(f"\n💰 Spread Analysis:")
spreads = []
for d in pepper_data:
    if d['bid_price_1'] and d['ask_price_1']:
        spread = d['ask_price_1'] - d['bid_price_1']
        spreads.append(spread)

if spreads:
    print(f"  Mean spread: {statistics.mean(spreads):.2f}")
    print(f"  Median spread: {statistics.median(spreads):.2f}")
    print(f"  Min spread: {min(spreads):.2f}")
    print(f"  Max spread: {max(spreads):.2f}")
    print(f"  Std spread: {statistics.stdev(spreads):.2f}")

# Look for patterns in price movements
print(f"\n🔎 Pattern Detection:")

# Check for momentum (if price went up, does it continue going up?)
momentum_correct = 0
momentum_total = 0

for i in range(10, len(price_changes)):
    recent = price_changes[i-10:i]
    avg_recent = statistics.mean(recent)
    next_change = price_changes[i]
    
    if abs(avg_recent) > 0.5:  # Significant momentum
        momentum_total += 1
        if (avg_recent > 0 and next_change > 0) or (avg_recent < 0 and next_change < 0):
            momentum_correct += 1

if momentum_total > 0:
    momentum_accuracy = momentum_correct / momentum_total
    print(f"  Momentum prediction accuracy: {momentum_accuracy:.2%}")
    if momentum_accuracy > 0.55:
        print(f"  ✅ Momentum strategy would work!")
    else:
        print(f"  ❌ Momentum strategy would fail")

# Analyze price levels and support/resistance
print(f"\n📊 Price Level Analysis:")

# Create histogram of price levels
price_rounded = [round(p / 10) * 10 for p in mid_prices]
price_freq = {}
for p in price_rounded:
    price_freq[p] = price_freq.get(p, 0) + 1

# Sort by frequency
sorted_prices = sorted(price_freq.items(), key=lambda x: x[1], reverse=True)

print(f"  Most common price levels (±5):")
for price, freq in sorted_prices[:10]:
    print(f"    {price:.0f}: {freq} times ({freq/len(mid_prices)*100:.1f}%)")

# Check if certain price levels act as support/resistance
print(f"\n🛡️  Support/Resistance Analysis:")

# Find local minima and maxima
local_minima = []
local_maxima = []

for i in range(50, len(mid_prices) - 50):
    window = mid_prices[i-50:i+50]
    current = mid_prices[i]
    
    if current == min(window):
        local_minima.append(current)
    elif current == max(window):
        local_maxima.append(current)

if local_minima:
    print(f"  Local minima: {min(local_minima):.1f} - {max(local_minima):.1f}")
if local_maxima:
    print(f"  Local maxima: {min(local_maxima):.1f} - {max(local_maxima):.1f}")

# Time series analysis
print(f"\n⏰ Time Series Analysis:")

# Divide into 10 segments and analyze each
segment_size = len(mid_prices) // 10
for seg in range(10):
    start = seg * segment_size
    end = start + segment_size
    segment_prices = mid_prices[start:end]
    
    seg_mean = statistics.mean(segment_prices)
    seg_std = statistics.stdev(segment_prices)
    seg_trend = (segment_prices[-1] - segment_prices[0]) / segment_prices[0] * 100
    
    print(f"  Segment {seg+1}: Mean {seg_mean:8.1f} | Std {seg_std:5.1f} | "
          f"Trend {seg_trend:+5.2f}%")

# FINAL RECOMMENDATION
print("\n" + "="*80)
print("STRATEGY RECOMMENDATION")
print("="*80)

# Based on analysis, recommend strategy
if reversion_rate > 0.55:
    print("""
✅ MEAN REVERSION STRATEGY RECOMMENDED

Pepper shows strong mean-reverting behavior!
Strategy:
- Calculate moving average (100-200 ticks)
- Buy when price dips below MA
- Sell when price rises above MA
- Tight position limits (±20)
- Quick entry/exit

Expected: Consistent small profits from oscillations
""")
elif momentum_accuracy > 0.55:
    print("""
✅ MOMENTUM/TREND FOLLOWING STRATEGY RECOMMENDED

Pepper shows trending behavior with momentum!
Strategy:
- Detect trend direction (up/down)
- Trade WITH the trend, not against it
- Use EMA crossover for trend detection
- Wider position limits when trend is strong
- Cut losses quickly when trend reverses

Expected: Profits from riding trends
""")
else:
    print("""
⚠️  MIXED/UNPREDICTABLE BEHAVIOR

Pepper shows neither strong mean reversion nor momentum.
Strategy:
- Conservative market making only
- Very tight position limits (±5-10)
- Wide spreads to avoid adverse selection
- Exit positions quickly
- Focus on earning spread, not directional bets

Expected: Small but consistent profits from spread
""")
