"""
Analyze v3.0 Performance - Both Products
"""

import json
import csv
from io import StringIO

with open('round1/123540.json', 'r') as f:
    data = json.load(f)

reader = csv.DictReader(StringIO(data['activitiesLog']), delimiter=';')
rows = list(reader)

print("="*80)
print("V3.0 PERFORMANCE ANALYSIS (Both Products)")
print("="*80)

print(f"\n📊 Overall Result:")
print(f"  Final PnL: {data['profit']:.2f} XIRECS")

# Separate by product
osmium_pnl = []
pepper_pnl = []

for row in rows:
    product = row['product']
    pnl = float(row['profit_and_loss'])
    
    if product == 'ASH_COATED_OSMIUM':
        osmium_pnl.append(pnl)
    elif product == 'INTARIAN_PEPPER_ROOT':
        pepper_pnl.append(pnl)

osmium_final = osmium_pnl[-1] if osmium_pnl else 0
pepper_final = pepper_pnl[-1] if pepper_pnl else 0

print(f"\n💰 Breakdown:")
print(f"  ASH_COATED_OSMIUM: {osmium_final:+.2f} XIRECS")
print(f"  INTARIAN_PEPPER_ROOT: {pepper_final:+.2f} XIRECS")
print(f"  Net: {data['profit']:+.2f} XIRECS")

print(f"\n📈 Version Comparison:")
print(f"  v1.0: -395.44 XIRECS (Osmium +1296, Pepper -1692)")
print(f"  v2.0: +1296.56 XIRECS (Osmium only)")
print(f"  v3.0: {data['profit']:+.2f} XIRECS (Osmium {osmium_final:+.0f}, Pepper {pepper_final:+.0f})")

# Pepper analysis
if pepper_pnl:
    print(f"\n🔍 Pepper Deep Dive:")
    print(f"  Max PnL: {max(pepper_pnl):+.2f}")
    print(f"  Min PnL: {min(pepper_pnl):+.2f}")
    
    # Find when Pepper started losing
    for i, pnl in enumerate(pepper_pnl):
        if pnl < 0:
            print(f"  First negative PnL at iteration {i}")
            break
    
    # Check trend
    early = pepper_pnl[:100]
    late = pepper_pnl[-100:]
    print(f"  Early avg (first 100): {sum(early)/len(early):+.2f}")
    print(f"  Late avg (last 100): {sum(late)/len(late):+.2f}")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)

if pepper_final < 0:
    print("""
❌ Pepper is STILL losing money in v3.0!

The conservative market making with LONG bias didn't work.
Possible reasons:
1. Spreads still too tight (adverse selection)
2. LONG bias not strong enough
3. Position limit still too high (±15)
4. Market making on trending product is inherently difficult

RECOMMENDATION:
- Revert to v2.0 (Osmium only) for +1296 XIRECS
- OR try even more conservative Pepper strategy:
  * Position limit: ±5 (very tight)
  * Spread: 10 points (very wide)
  * Only market make, no directional bias
""")
else:
    print("""
✅ Pepper is profitable in v3.0!

""")
