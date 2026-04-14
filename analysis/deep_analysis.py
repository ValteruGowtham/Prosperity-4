"""
Deep Analysis of Round 1 Trading Activity
Focus: Understanding EXACTLY what went wrong with INTARIAN_PEPPER_ROOT
"""

import json
import csv
from io import StringIO
from collections import defaultdict

# Load JSON results
with open('round1/119569.json', 'r') as f:
    data = json.load(f)

# Parse activities log
activities_log = data['activitiesLog']
reader = csv.DictReader(StringIO(activities_log), delimiter=';')
rows = list(reader)

print("="*80)
print("DEEP DIVE: INTARIAN_PEPPER_ROOT TRADING ACTIVITY")
print("="*80)

# Track PnL changes to identify trades
print("\n📊 Analyzing PnL Changes (proxy for trades)...")

pepper_data = [(int(row['timestamp']), 
                float(row['profit_and_loss']),
                float(row['mid_price']),
                float(row['bid_price_1']) if row['bid_price_1'] else None,
                float(row['ask_price_1']) if row['ask_price_1'] else None,
                int(row['bid_volume_1']) if row['bid_volume_1'] else None,
                int(row['ask_volume_1']) if row['ask_volume_1'] else None)
               for row in rows if row['product'] == 'INTARIAN_PEPPER_ROOT']

osmium_data = [(int(row['timestamp']), 
                float(row['profit_and_loss']),
                float(row['mid_price']))
               for row in rows if row['product'] == 'ASH_COATED_OSMIUM']

# Find all PnL changes
print("\n🔍 INTARIAN_PEPPER_ROOT PnL Changes:")
print("-" * 80)

trade_events = []
for i in range(1, len(pepper_data)):
    ts, pnl, mid, bid1, ask1, bid_vol, ask_vol = pepper_data[i]
    prev_ts, prev_pnl, prev_mid, _, _, _, _ = pepper_data[i-1]
    
    pnl_change = pnl - prev_pnl
    
    if abs(pnl_change) > 0.1:  # Significant change
        trade_events.append({
            'timestamp': ts,
            'pnl': pnl,
            'pnl_change': pnl_change,
            'mid_price': mid,
            'bid': bid1,
            'ask': ask1,
        })

print(f"Total significant PnL changes: {len(trade_events)}")

# Show first 20 and last 20 events
print("\n📈 First 20 PnL Change Events:")
for event in trade_events[:20]:
    direction = "📈" if event['pnl_change'] > 0 else "📉"
    print(f"  t={event['timestamp']:6d} | PnL: {event['pnl']:+8.2f} | "
          f"Change: {event['pnl_change']:+6.2f} | "
          f"Mid: {event['mid_price']:8.1f} | "
          f"Bid: {event['bid'] or 'N/A':6} | Ask: {event['ask'] or 'N/A':6}")

print(f"\n📉 Last 20 PnL Change Events:")
for event in trade_events[-20:]:
    direction = "📈" if event['pnl_change'] > 0 else "📉"
    print(f"  t={event['timestamp']:6d} | PnL: {event['pnl']:+8.2f} | "
          f"Change: {event['pnl_change']:+6.2f} | "
          f"Mid: {event['mid_price']:8.1f} | "
          f"Bid: {event['bid'] or 'N/A':6} | Ask: {event['ask'] or 'N/A':6}")

# Analyze position buildup
print("\n" + "="*80)
print("INFERRING POSITION BUILDUP")
print("="*80)

# Estimate position from PnL slope
# If PnL is decreasing while price is increasing → we're short
# If PnL is increasing while price is increasing → we're long

print("\n📊 Position Inference (PnL vs Price correlation):")
print("-" * 80)

# Group into 10K intervals
intervals = []
for i in range(0, len(pepper_data), 500):
    chunk = pepper_data[i:i+500]
    if len(chunk) > 1:
        ts_start = chunk[0][0]
        ts_end = chunk[-1][0]
        pnl_start = chunk[0][1]
        pnl_end = chunk[-1][1]
        price_start = chunk[0][2]
        price_end = chunk[-1][2]
        
        pnl_change = pnl_end - pnl_start
        price_change = price_end - price_start
        
        # Correlation: same direction = long, opposite = short
        if price_change > 0 and pnl_change < 0:
            position = "SHORT ❌"
        elif price_change > 0 and pnl_change > 0:
            position = "LONG ✅"
        elif price_change < 0 and pnl_change > 0:
            position = "SHORT ✅"
        elif price_change < 0 and pnl_change < 0:
            position = "LONG ❌"
        else:
            position = "FLAT"
        
        print(f"  t={ts_start:6d}-{ts_end:6d} | Price: {price_start:7.1f}→{price_end:7.1f} "
              f"({price_change:+6.1f}) | PnL: {pnl_start:7.1f}→{pnl_end:7.1f} "
              f"({pnl_change:+6.1f}) | Position: {position}")

# Check order placement patterns
print("\n" + "="*80)
print("ORDER PLACEMENT ANALYSIS")
print("="*80)

print("\n📊 Sample Order Book States (every 10K ticks):")
print("-" * 80)

for i in range(0, len(pepper_data), 500):
    ts, pnl, mid, bid1, ask1, bid_vol, ask_vol = pepper_data[i]
    
    if bid1 and ask1:
        spread = ask1 - bid1
        mid_distance_bid = mid - bid1
        mid_distance_ask = ask1 - mid
        
        print(f"  t={ts:6d} | Mid: {mid:8.1f} | Bid: {bid1:8.1f} (+{bid_vol}) | "
              f"Ask: {ask1:8.1f} ({ask_vol}) | Spread: {spread:4.1f} | "
              f"PnL: {pnl:+8.1f}")

# Compare with Osmium
print("\n" + "="*80)
print("COMPARISON: ASH_COATED_OSMIUM vs INTARIAN_PEPPER_ROOT")
print("="*80)

osmium_final_pnl = osmium_data[-1][1] if osmium_data else 0
pepper_final_pnl = pepper_data[-1][1] if pepper_data else 0
osmium_price_range = max(m for _, m, _ in osmium_data) - min(m for _, m, _ in osmium_data)
pepper_price_range = max(m for _, m, _, _, _, _, _ in pepper_data) - min(m for _, m, _, _, _, _, _ in pepper_data)

print(f"\n  Metric                    | OSMIUM      | PEPPER")
print(f"  {'-'*60}")
print(f"  Final PnL                 | {osmium_final_pnl:+11.2f} | {pepper_final_pnl:+11.2f}")
print(f"  Price Range               | {osmium_price_range:11.1f} | {pepper_price_range:11.1f}")
print(f"  Price Volatility          | {'LOW' if osmium_price_range < 50 else 'HIGH':11} | {'LOW' if pepper_price_range < 50 else 'HIGH'}")

# Key insight
print("\n" + "="*80)
print("KEY INSIGHTS")
print("="*80)

print(f"""
1. INTARIAN_PEPPER_ROOT price moved ~100 points over the round
2. Our PnL went from 0 to -1692 (losing ~17 XIRECS per point of price movement)
3. This suggests we held ~17 units SHORT on average
4. Position limit is 40, so we were likely maxed out short
5. The algorithm kept selling as price went up (mean-reversion bias)
6. But price NEVER mean-reverted - it kept trending up

PROBLEM: Our "trend following" strategy is actually mean-reverting!
We're placing sells when price is high (above EMA) but price keeps going higher.
""")

# Show specific problematic patterns
print("\n" + "="*80)
print("SPECIFIC FAILURE PATTERNS")
print("="*80)

# Find periods where we lost the most
worst_periods = []
for i in range(100, len(pepper_data)):
    chunk = pepper_data[i-100:i]
    pnl_loss = chunk[0][1] - chunk[-1][1]
    if pnl_loss > 10:  # Lost more than 10 in 100 ticks
        worst_periods.append({
            'start_ts': chunk[0][0],
            'end_ts': chunk[-1][0],
            'pnl_loss': pnl_loss,
            'price_change': chunk[-1][2] - chunk[0][2]
        })

print(f"\nTop 10 Worst Periods (100-tick windows):")
worst_periods.sort(key=lambda x: x['pnl_loss'], reverse=True)
for period in worst_periods[:10]:
    print(f"  t={period['start_ts']:6d}-{period['end_ts']:6d} | "
          f"PnL Loss: {period['pnl_loss']:-7.1f} | "
          f"Price Change: {period['price_change']:+6.1f}")
