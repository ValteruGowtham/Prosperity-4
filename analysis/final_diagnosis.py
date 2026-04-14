"""
Final Diagnosis: INTARIAN_PEPPER_ROOT Position Analysis
Calculate exact position held over time
"""

import json
import csv
from io import StringIO

with open('round1/119569.json', 'r') as f:
    data = json.load(f)

reader = csv.DictReader(StringIO(data['activitiesLog']), delimiter=';')
rows = list(reader)

pepper_data = [(int(row['timestamp']), float(row['profit_and_loss']), float(row['mid_price']))
               for row in rows if row['product'] == 'INTARIAN_PEPPER_ROOT']

print("="*80)
print("POSITION SIZE INFERENCE FROM PnL SLOPE")
print("="*80)

print("""
Methodology:
- PnL change per tick = -Position × Price change per tick
- If PnL drops by 4 per tick while price is stable, position = 0 (no change)
- If PnL drops by X per tick while price rises by 1, position = -X (short)
""")

print("\n📊 Estimated Position Over Time:")
print("-" * 80)

# Calculate position from PnL slope
positions = []
for i in range(100, len(pepper_data), 100):
    chunk = pepper_data[i-100:i]
    
    # Get PnL change and price change
    pnl_start = chunk[0][1]
    pnl_end = chunk[-1][1]
    price_start = chunk[0][2]
    price_end = chunk[-1][2]
    
    pnl_change = pnl_end - pnl_start
    price_change = price_end - price_start
    ticks = 100
    
    # Average PnL change per tick
    pnl_per_tick = pnl_change / ticks
    
    # If price is rising and PnL is falling, we're short
    # Position ≈ -PnL_change / Price_change (if price_change != 0)
    if abs(price_change) > 0.1:
        estimated_position = -pnl_change / price_change
    else:
        estimated_position = 0
    
    positions.append({
        'timestamp': chunk[-1][0],
        'pnl': pnl_end,
        'price': price_end,
        'pnl_per_tick': pnl_per_tick,
        'estimated_position': estimated_position,
    })
    
    # Show every 1000 ticks
    if i % 1000 == 0:
        pos = positions[-1]
        pos_str = "SHORT" if pos['estimated_position'] < 0 else "LONG"
        print(f"  t={pos['timestamp']:6d} | PnL: {pos['pnl']:+8.1f} | "
              f"Price: {pos['price']:8.1f} | PnL/tick: {pos['pnl_per_tick']:+5.2f} | "
              f"Est. Position: {pos['estimated_position']:+5.1f} ({pos_str})")

print("\n" + "="*80)
print("CRITICAL FINDING")
print("="*80)

print("""
The PnL slope shows:
- Early game: PnL declining ~0.6 per tick
- Late game: PnL declining ~4.0 per tick

This means:
1. We accumulated a SHORT position early
2. The position grew over time (or we got worse fills)
3. By late game, we're maxed SHORT (~40 units)
4. Price keeps rising → PnL keeps falling

The -4.0 per tick in late game with stable price means:
- We're NOT trading actively
- We're just holding a short position
- Mark-to-market losses accumulate

ROOT CAUSE:
Our algorithm placed sell orders, got filled, and kept the short position.
As price rose from 12000 → 12100, our short position lost value continuously.
We never covered (bought back) because our algorithm kept trying to sell more!

This is the OPPOSITE of trend following - it's trend fighting!
""")

# Show exact PnL per tick pattern
print("\n📉 PnL Per Tick Analysis (sample):")
print("-" * 80)

for i in range(1, min(50, len(pepper_data))):
    ts, pnl, mid = pepper_data[i]
    prev_ts, prev_pnl, prev_mid = pepper_data[i-1]
    
    pnl_change = pnl - prev_pnl
    if abs(pnl_change) > 0.01:
        print(f"  t={ts:6d} | PnL: {pnl:+8.2f} | Change: {pnl_change:+6.2f} | "
              f"Mid: {mid:8.1f} | Price Δ: {mid - prev_mid:+5.1f}")

print("\n" + "="*80)
print("SOLUTION")
print("="*80)

print("""
FIX 1: Don't trade INTARIAN_PEPPER_ROOT at all
- Just skip it, focus on ASH_COATED_OSMIUM which works (+1296 XIRECS)
- Net result: +1296 instead of -395

FIX 2: Trade Pepper with LONG bias only
- Only place BUY orders, never SELL
- Follow the trend instead of fighting it
- Use wider spreads to avoid getting run over

FIX 3: Conservative market making on Pepper
- Very tight position limits (±5 instead of ±40)
- Quick mean reversion scalping
- Exit positions immediately when they form

RECOMMENDATION: FIX 1 (skip Pepper entirely)
- Osmium alone gives +1296 XIRECS
- Adding Pepper risk is not worth it until strategy is proven
""")
