"""
Deep Forensic Analysis: INTARIAN_PEPPER_ROOT v3.0 Performance
Goal: Find ANY exploitable pattern or understand exact failure mode
"""

import json
import csv
from io import StringIO
import statistics

with open('round1/123540.json', 'r') as f:
    data = json.load(f)

reader = csv.DictReader(StringIO(data['activitiesLog']), delimiter=';')
rows = list(reader)

# Extract Pepper data with full details
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
print("PEPPER FORENSIC ANALYSIS - v3.0 Performance")
print("="*80)

# 1. Timeline of PnL degradation
print("\n📉 PnL Degradation Timeline:")
print("-" * 80)

# Find key inflection points
inflection_points = []
for i in range(1, len(pepper_data)):
    curr_pnl = pepper_data[i]['pnl']
    prev_pnl = pepper_data[i-1]['pnl']
    
    if abs(curr_pnl - prev_pnl) > 1.0:  # Significant change
        inflection_points.append({
            'timestamp': pepper_data[i]['timestamp'],
            'pnl': curr_pnl,
            'change': curr_pnl - prev_pnl,
            'mid_price': pepper_data[i]['mid_price'],
            'index': i
        })

print(f"Total significant PnL changes: {len(inflection_points)}")

# Show first 10 and last 10
print("\nFirst 10 PnL changes:")
for pt in inflection_points[:10]:
    direction = "📈" if pt['change'] > 0 else "📉"
    print(f"  t={pt['timestamp']:6d} | PnL: {pt['pnl']:+8.2f} | Δ: {pt['change']:+6.2f} | "
          f"Price: {pt['mid_price']:8.1f}")

print("\nLast 10 PnL changes:")
for pt in inflection_points[-10:]:
    direction = "📈" if pt['change'] > 0 else "📉"
    print(f"  t={pt['timestamp']:6d} | PnL: {pt['pnl']:+8.2f} | Δ: {pt['change']:+6.2f} | "
          f"Price: {pt['mid_price']:8.1f}")

# 2. Position inference from PnL slope
print("\n" + "="*80)
print("POSITION INFERENCE (From PnL vs Price Relationship)")
print("="*80)

# When PnL decreases while price is stable → we're short
# When PnL increases while price is stable → we're long
# When PnL decreases while price increases → we're short

print("\nAnalyzing position over time windows:")
print("-" * 80)

for window_start in [0, 100, 200, 300, 400, 500, 600, 700, 800, 900]:
    chunk = pepper_data[window_start*100:(window_start+1)*100]
    if len(chunk) < 50:
        continue
    
    pnl_start = chunk[0]['pnl']
    pnl_end = chunk[-1]['pnl']
    price_start = chunk[0]['mid_price']
    price_end = chunk[-1]['mid_price']
    
    pnl_change = pnl_end - pnl_start
    price_change = price_end - price_start
    
    # Infer position
    if abs(price_change) > 1:
        # Position ≈ -PnL_change / Price_change
        est_position = -pnl_change / price_change
    else:
        # Price stable, PnL change = 0 (no position change)
        est_position = 0
    
    pos_type = "SHORT" if est_position < -0.5 else ("LONG" if est_position > 0.5 else "FLAT")
    
    print(f"  t={chunk[0]['timestamp']:6d}-{chunk[-1]['timestamp']:6d} | "
          f"Price: {price_start:7.1f}→{price_end:7.1f} ({price_change:+5.1f}) | "
          f"PnL: {pnl_start:7.1f}→{pnl_end:7.1f} ({pnl_change:+5.1f}) | "
          f"Est Position: {est_position:+5.1f} ({pos_type})")

# 3. Price level analysis - when did we lose money?
print("\n" + "="*80)
print("LOSS ANALYSIS BY PRICE LEVEL")
print("="*80)

# Group PnL changes by price range
price_ranges = [(11995, 12020), (12020, 12040), (12040, 12060), (12060, 12080), (12080, 12110)]

print("\nPnL changes by price range:")
for low, high in price_ranges:
    changes_in_range = []
    for pt in inflection_points:
        if low <= pt['mid_price'] <= high:
            changes_in_range.append(pt['change'])
    
    if changes_in_range:
        total = sum(changes_in_range)
        avg = statistics.mean(changes_in_range)
        pos_changes = len([c for c in changes_in_range if c > 0])
        neg_changes = len([c for c in changes_in_range if c < 0])
        
        print(f"  Price {low:.0f}-{high:.0f}: "
              f"Total Δ: {total:+7.1f} | Avg: {avg:+6.2f} | "
              f"Pos: {pos_changes} | Neg: {neg_changes}")

# 4. Spread behavior when losing money
print("\n" + "="*80)
print("SPREAD ANALYSIS DURING LOSSES")
print("="*80)

losing_periods = []
for pt in inflection_points:
    if pt['change'] < -0.5:
        losing_periods.append(pt)

if losing_periods:
    print(f"\nLosing trades ({len(losing_periods)} events):")
    print(f"  Avg price during losses: {statistics.mean([p['mid_price'] for p in losing_periods]):.1f}")
    print(f"  Avg loss per event: {statistics.mean([p['change'] for p in losing_periods]):.2f}")
    print(f"  Max single loss: {min([p['change'] for p in losing_periods]):.2f}")
    
    # Check if losses correlate with spread width
    print(f"\nSpread during losing periods:")
    spreads_during_loss = []
    for pt in losing_periods[:20]:  # Sample
        # Find corresponding row
        for d in pepper_data:
            if d['timestamp'] == pt['timestamp'] and d['bid_price_1'] and d['ask_price_1']:
                spread = d['ask_price_1'] - d['bid_price_1']
                spreads_during_loss.append(spread)
                break
    
    if spreads_during_loss:
        print(f"  Avg spread: {statistics.mean(spreads_during_loss):.2f}")
        print(f"  Min spread: {min(spreads_during_loss):.2f}")
        print(f"  Max spread: {max(spreads_during_loss):.2f}")

# 5. Time-based analysis - when did losses accelerate?
print("\n" + "="*80)
print("TIME-BASED LOSS ACCELERATION")
print("="*80)

# Divide into 10 segments
segment_size = len(pepper_data) // 10
print("\nPnL by time segment:")
for seg in range(10):
    start = seg * segment_size
    end = start + segment_size
    segment = pepper_data[start:end]
    
    if segment:
        pnl_start = segment[0]['pnl']
        pnl_end = segment[-1]['pnl']
        pnl_change = pnl_end - pnl_start
        
        print(f"  Segment {seg+1:2d} (t={segment[0]['timestamp']:6d}-{segment[-1]['timestamp']:6d}): "
              f"PnL {pnl_start:7.1f}→{pnl_end:7.1f} (Δ{pnl_change:+6.1f})")

# 6. Key question: Did we get filled on wrong side?
print("\n" + "="*80)
print("ADVERSE SELECTION ANALYSIS")
print("="*80)

# If we're market making:
# - We buy when price is about to drop (bad)
# - We sell when price is about to rise (bad)
# Check if PnL drops AFTER we trade

print("\nChecking for adverse selection pattern:")
print("-" * 80)

adverse_events = 0
total_trades = 0

for i in range(1, len(pepper_data) - 5):
    curr_pnl = pepper_data[i]['pnl']
    prev_pnl = pepper_data[i-1]['pnl']
    
    if abs(curr_pnl - prev_pnl) > 0.3:  # Trade happened
        total_trades += 1
        
        # Check next 5 ticks
        future_pnl = pepper_data[i+5]['pnl']
        future_price = pepper_data[i+5]['mid_price']
        current_price = pepper_data[i]['mid_price']
        
        # If we lost money in next 5 ticks after trading
        if future_pnl < curr_pnl - 0.5:
            adverse_events += 1

if total_trades > 0:
    adverse_rate = adverse_events / total_trades
    print(f"  Total trades: {total_trades}")
    print(f"  Adverse selection events: {adverse_events}")
    print(f"  Adverse selection rate: {adverse_rate:.1%}")
    
    if adverse_rate > 0.5:
        print(f"  ⚠️  HIGH adverse selection! Bots are trading against us!")
    else:
        print(f"  ✅ Low adverse selection")

# 7. FINAL DIAGNOSIS
print("\n" + "="*80)
print("FINAL DIAGNOSIS & HYPOTHESES")
print("="*80)

print("""
Based on the forensic analysis, here are the likely causes:

HYPOTHESIS 1: Position Accumulation
- Pepper drifts upward steadily
- Our market making gets filled more on SHORT side (selling)
- We accumulate SHORT position over time
- As price rises, SHORT position loses value
- Even with LONG bias, we still get more SHORT fills

HYPOTHESIS 2: Adverse Selection
- Bots know the trend direction
- They trade against our market making orders
- We buy before price drops, sell before price rises
- Net result: Consistent small losses

HYPOTHESIS 3: Spread Too Tight
- Average spread is 13.71
- Our half-spread of 7 means we're too aggressive
- We get picked off by informed traders
- Need wider spreads to compensate

HYPOTHESIS 4: Trend + Market Making Incompatibility
- Market making works best in range-bound markets
- Pepper has steady upward drift (not range-bound)
- Market making on trending asset = losses
- Should use directional strategy instead

TO TEST THESE HYPOTHESES:
1. Check if position is SHORT or LONG (from PnL slope)
2. Measure adverse selection rate
3. Test wider spreads (10-15 points)
4. Test pure directional LONG strategy
""")
