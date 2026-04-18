"""
Analyze Round 1 Performance Results
Parse JSON, LOG files and provide detailed performance breakdown
"""

import json
import csv
from io import StringIO
from collections import defaultdict

# Load JSON results
with open('round1/119569.json', 'r') as f:
    json_data = json.load(f)

# Load LOG results
with open('round1/119569.log', 'r') as f:
    log_data = json.load(f)

print("="*80)
print("PROSPERITY 4 - ROUND 1 PERFORMANCE ANALYSIS")
print("="*80)

print(f"\n📊 Overall Results:")
print(f"  Round: {json_data['round']}")
print(f"  Status: {json_data['status']}")
print(f"  Final PnL: {json_data['profit']:.2f} XIRECS")
if 'submissionId' in json_data:
    print(f"  Submission ID: {json_data['submissionId']}")

# Parse activities log
activities_log = json_data['activitiesLog']
lines = activities_log.strip().split('\n')

# Parse CSV data
reader = csv.DictReader(StringIO(activities_log), delimiter=';')
rows = list(reader)

print(f"\n📈 Iteration Statistics:")
print(f"  Total iterations: {len(rows)}")

# Analyze PnL over time
osmium_pnl = []
pepper_pnl = []
osmium_mid = []
pepper_mid = []

for row in rows:
    product = row['product']
    pnl = float(row['profit_and_loss'])
    mid = float(row['mid_price'])
    timestamp = int(row['timestamp'])
    
    if product == 'ASH_COATED_OSMIUM':
        osmium_pnl.append((timestamp, pnl))
        osmium_mid.append((timestamp, mid))
    elif product == 'INTARIAN_PEPPER_ROOT':
        pepper_pnl.append((timestamp, pnl))
        pepper_mid.append((timestamp, mid))

print(f"\n💰 PnL Breakdown by Product:")
if osmium_pnl:
    final_osmium = osmium_pnl[-1][1]
    print(f"  ASH_COATED_OSMIUM: {final_osmium:+.2f} XIRECS")
if pepper_pnl:
    final_pepper = pepper_pnl[-1][1]
    print(f"  INTARIAN_PEPPER_ROOT: {final_pepper:+.2f} XIRECS")

# PnL evolution
print(f"\n📉 PnL Evolution (ASH_COATED_OSMIUM):")
print(f"  Start: {osmium_pnl[0][1]:.2f}")
print(f"  End: {osmium_pnl[-1][1]:.2f}")

# Find max and min PnL
osmium_pnl_values = [pnl for _, pnl in osmium_pnl]
print(f"  Max PnL: {max(osmium_pnl_values):.2f}")
print(f"  Min PnL: {min(osmium_pnl_values):.2f}")
print(f"  Max Drawdown: {min(osmium_pnl_values) - max(osmium_pnl_values):.2f}")

print(f"\n📈 PnL Evolution (INTARIAN_PEPPER_ROOT):")
if pepper_pnl:
    print(f"  Start: {pepper_pnl[0][1]:.2f}")
    print(f"  End: {pepper_pnl[-1][1]:.2f}")
    pepper_pnl_values = [pnl for _, pnl in pepper_pnl]
    print(f"  Max PnL: {max(pepper_pnl_values):.2f}")
    print(f"  Min PnL: {min(pepper_pnl_values):.2f}")

# Price evolution
print(f"\n💎 Price Evolution (ASH_COATED_OSMIUM):")
print(f"  Start: {osmium_mid[0][1]:.2f}")
print(f"  End: {osmium_mid[-1][1]:.2f}")
print(f"  Range: {min(m for _, m in osmium_mid):.2f} - {max(m for _, m in osmium_mid):.2f}")

print(f"\n🍅 Price Evolution (INTARIAN_PEPPER_ROOT):")
if pepper_mid:
    print(f"  Start: {pepper_mid[0][1]:.2f}")
    print(f"  End: {pepper_mid[-1][1]:.2f}")
    print(f"  Range: {min(m for _, m in pepper_mid):.2f} - {max(m for _, m in pepper_mid):.2f}")

# Analyze when PnL changed
print(f"\n🔍 Key Events (PnL changes in ASH_COATED_OSMIUM):")
changes = []
for i in range(1, len(osmium_pnl)):
    ts, pnl = osmium_pnl[i]
    prev_ts, prev_pnl = osmium_pnl[i-1]
    if abs(pnl - prev_pnl) > 0.01:
        changes.append((ts, pnl - prev_pnl, pnl))

print(f"  Total PnL change events: {len(changes)}")
if changes:
    positive = [c for c in changes if c[1] > 0]
    negative = [c for c in changes if c[1] < 0]
    print(f"  Positive changes: {len(positive)}")
    print(f"  Negative changes: {len(negative)}")
    print(f"  Avg positive change: {sum(c[1] for c in positive)/len(positive):.2f}")
    print(f"  Avg negative change: {sum(c[1] for c in negative)/len(negative):.2f}")

# Check Pepper PnL events
if pepper_pnl:
    print(f"\n🔍 Key Events (PnL changes in INTARIAN_PEPPER_ROOT):")
    pepper_changes = []
    for i in range(1, len(pepper_pnl)):
        ts, pnl = pepper_pnl[i]
        prev_ts, prev_pnl = pepper_pnl[i-1]
        if abs(pnl - prev_pnl) > 0.01:
            pepper_changes.append((ts, pnl - prev_pnl, pnl))
    
    print(f"  Total PnL change events: {len(pepper_changes)}")
    if pepper_changes:
        positive = [c for c in pepper_changes if c[1] > 0]
        negative = [c for c in pepper_changes if c[1] < 0]
        print(f"  Positive changes: {len(positive)}")
        print(f"  Negative changes: {len(negative)}")
        if positive:
            print(f"  Avg positive change: {sum(c[1] for c in positive)/len(positive):.2f}")
        if negative:
            print(f"  Avg negative change: {sum(c[1] for c in negative)/len(negative):.2f}")

print("\n" + "="*80)
print("DIAGNOSIS")
print("="*80)

final_pnl = json_data['profit']
if final_pnl < 0:
    print("\n❌ NEGATIVE PnL - Algorithm is losing money")
    print("\nPossible issues:")
    
    # Check if Osmium is making money
    if osmium_pnl and osmium_pnl[-1][1] > 0:
        print("  ✅ ASH_COATED_OSMIUM is profitable")
    else:
        print("  ❌ ASH_COATED_OSMIUM is losing money")
    
    # Check if Pepper is making money
    if pepper_pnl:
        if pepper_pnl[-1][1] > 0:
            print("  ✅ INTARIAN_PEPPER_ROOT is profitable")
        else:
            print("  ❌ INTARIAN_PEPPER_ROOT is losing money")
    
    # Check if issue is asymmetric
    if osmium_pnl and pepper_pnl:
        osmium_final = osmium_pnl[-1][1]
        pepper_final = pepper_pnl[-1][1]
        
        if osmium_final > 0 and pepper_final < 0:
            print(f"\n⚠️  Main issue: INTARIAN_PEPPER_ROOT losses are dragging down overall PnL")
            print(f"     Osmium profit: +{osmium_final:.2f}")
            print(f"     Pepper loss: {pepper_final:.2f}")
            print(f"     Net: {final_pnl:.2f}")
        elif osmium_final < 0 and pepper_final > 0:
            print(f"\n⚠️  Main issue: ASH_COATED_OSMIUM losses are dragging down overall PnL")
else:
    print("\n✅ POSITIVE PnL - Algorithm is profitable!")

print("\n" + "="*80)
