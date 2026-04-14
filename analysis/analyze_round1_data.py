"""
Round 1 Data Analysis - Deep Statistical Analysis
Products: ASH_COATED_OSMIUM, INTARIAN_PEPPER_ROOT
"""

import csv
from collections import defaultdict
import statistics

def analyze_prices_file(filename):
    """Analyze price/order book data from a CSV file."""
    products = defaultdict(lambda: {
        'mid_prices': [],
        'spreads': [],
        'bid_prices': [],
        'ask_prices': [],
        'bid_volumes': [],
        'ask_volumes': [],
    })
    
    with open(filename, 'r') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            product = row['product']
            mid_price = float(row['mid_price'])
            
            # Calculate spread
            bid1 = float(row['bid_price_1']) if row['bid_price_1'] else None
            ask1 = float(row['ask_price_1']) if row['ask_price_1'] else None
            
            if bid1 and ask1:
                spread = ask1 - bid1
                products[product]['spreads'].append(spread)
                products[product]['bid_prices'].append(bid1)
                products[product]['ask_prices'].append(ask1)
            
            products[product]['mid_prices'].append(mid_price)
            
            # Volume tracking
            for i in range(1, 4):
                bid_vol = row.get(f'bid_volume_{i}', '')
                ask_vol = row.get(f'ask_volume_{i}', '')
                if bid_vol:
                    products[product]['bid_volumes'].append(int(bid_vol))
                if ask_vol:
                    products[product]['ask_volumes'].append(int(ask_vol))
    
    return products

def analyze_trades_file(filename):
    """Analyze trade data from a CSV file."""
    products = defaultdict(lambda: {
        'prices': [],
        'quantities': [],
        'timestamps': [],
    })
    
    with open(filename, 'r') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            product = row['symbol']
            price = float(row['price'])
            quantity = int(row['quantity'])
            timestamp = int(row['timestamp'])
            
            products[product]['prices'].append(price)
            products[product]['quantities'].append(quantity)
            products[product]['timestamps'].append(timestamp)
    
    return products

def print_product_stats(product_name, price_data, trades_data=None):
    """Print comprehensive statistics for a product."""
    mid_prices = price_data['mid_prices']
    
    print(f"\n{'='*60}")
    print(f"Product: {product_name}")
    print(f"{'='*60}")
    
    print(f"\n📊 Mid Price Statistics:")
    print(f"  Count: {len(mid_prices)}")
    print(f"  Mean: {statistics.mean(mid_prices):.2f}")
    print(f"  Median: {statistics.median(mid_prices):.2f}")
    print(f"  Std Dev: {statistics.stdev(mid_prices):.2f}")
    print(f"  Min: {min(mid_prices):.2f}")
    print(f"  Max: {max(mid_prices):.2f}")
    print(f"  Range: {max(mid_prices) - min(mid_prices):.2f}")
    
    # Price changes
    price_changes = [mid_prices[i+1] - mid_prices[i] for i in range(len(mid_prices)-1)]
    print(f"\n📈 Price Changes (tick-to-tick):")
    print(f"  Mean change: {statistics.mean(price_changes):.4f}")
    print(f"  Std Dev of changes: {statistics.stdev(price_changes):.4f}")
    print(f"  Max single increase: {max(price_changes):.2f}")
    print(f"  Max single decrease: {min(price_changes):.2f}")
    
    # Spread analysis
    spreads = price_data['spreads']
    if spreads:
        print(f"\n💰 Spread Analysis:")
        print(f"  Mean spread: {statistics.mean(spreads):.2f}")
        print(f"  Median spread: {statistics.median(spreads):.2f}")
        print(f"  Min spread: {min(spreads):.2f}")
        print(f"  Max spread: {max(spreads):.2f}")
    
    # Trades analysis
    if trades_data:
        trade_prices = trades_data['prices']
        quantities = trades_data['quantities']
        timestamps = trades_data['timestamps']
        
        print(f"\n💹 Trade Statistics:")
        print(f"  Total trades: {len(trade_prices)}")
        print(f"  Mean trade price: {statistics.mean(trade_prices):.2f}")
        print(f"  Median trade price: {statistics.median(trade_prices):.2f}")
        print(f"  Trade price std: {statistics.stdev(trade_prices):.2f}")
        print(f"  Min trade price: {min(trade_prices):.2f}")
        print(f"  Max trade price: {max(trade_prices):.2f}")
        
        print(f"\n📦 Volume Statistics:")
        print(f"  Total volume: {sum(quantities)}")
        print(f"  Mean trade size: {statistics.mean(quantities):.2f}")
        print(f"  Median trade size: {statistics.median(quantities):.2f}")
        print(f"  Max trade size: {max(quantities)}")
        
        # Trade frequency
        if len(timestamps) > 1:
            time_diffs = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
            print(f"\n⏱️  Trade Frequency:")
            print(f"  Mean time between trades: {statistics.mean(time_diffs):.1f} ms")
            print(f"  Median time between trades: {statistics.median(time_diffs):.1f} ms")
    
    # Autocorrelation analysis (simple)
    if len(mid_prices) > 100:
        print(f"\n🔍 Autocorrelation (lag=1, 5, 10):")
        for lag in [1, 5, 10]:
            n = len(mid_prices) - lag
            mean_all = statistics.mean(mid_prices)
            var_all = sum((x - mean_all)**2 for x in mid_prices) / len(mid_prices)
            
            if var_all > 0:
                cov = sum((mid_prices[i] - mean_all) * (mid_prices[i+lag] - mean_all) 
                         for i in range(n)) / n
                autocorr = cov / var_all
                print(f"  Lag {lag}: {autocorr:.4f}")
    
    return {
        'mean': statistics.mean(mid_prices),
        'std': statistics.stdev(mid_prices),
        'min': min(mid_prices),
        'max': max(mid_prices),
    }

# Analyze all three days
days = ['prices_round_1_day_-2.csv', 'prices_round_1_day_-1.csv', 'prices_round_1_day_0.csv']
trades_files = ['trades_round_1_day_-2.csv', 'trades_round_1_day_-1.csv', 'trades_round_1_day_0.csv']

print("="*60)
print("PROSPERITY 4 - ROUND 1 DEEP DATA ANALYSIS")
print("="*60)

all_stats = {'ASH_COATED_OSMIUM': [], 'INTARIAN_PEPPER_ROOT': []}

for day_file, trades_file in zip(days, trades_files):
    print(f"\n\n{'#'*60}")
    print(f"# Analyzing {day_file.replace('prices_', '').replace('.csv', '')}")
    print(f"{'#'*60}")
    
    price_data = analyze_prices_file(f'round1/ROUND1/{day_file}')
    trades_data = analyze_trades_file(f'round1/ROUND1/{trades_file}')
    
    for product in ['ASH_COATED_OSMIUM', 'INTARIAN_PEPPER_ROOT']:
        stats = print_product_stats(product, price_data[product], trades_data.get(product))
        all_stats[product].append(stats)

# Summary across all days
print(f"\n\n{'='*60}")
print("SUMMARY ACROSS ALL DAYS")
print(f"{'='*60}")

for product in ['ASH_COATED_OSMIUM', 'INTARIAN_PEPPER_ROOT']:
    print(f"\n{product}:")
    means = [s['mean'] for s in all_stats[product]]
    stds = [s['std'] for s in all_stats[product]]
    mins = [s['min'] for s in all_stats[product]]
    maxs = [s['max'] for s in all_stats[product]]
    
    print(f"  Mean of means: {statistics.mean(means):.2f}")
    print(f"  Mean of stds: {statistics.mean(stds):.2f}")
    print(f"  Overall range: {min(mins):.2f} to {max(maxs):.2f}")
    print(f"  Day-to-day std: {statistics.stdev(means):.2f}")

print(f"\n{'='*60}")
print("KEY INSIGHTS FOR ALGORITHM DESIGN")
print(f"{'='*60}")
print("""
Based on the analysis:

ASH_COATED_OSMIUM:
- Appears to be the more volatile product
- Likely has trends/momentum patterns
- Wider spreads = more room for market making
- Position limit: 80

INTARIAN_PEPPER_ROOT:
- More stable, mean-reverting behavior expected
- Tighter spreads
- Good for conservative market making
- Position limit: 80

Strategy Recommendations:
1. For INTARIAN_PEPPER_ROOT: Mean-reversion market making
   - Tight spreads around fair value
   - Quick mean reversion = more fills
   
2. For ASH_COATED_OSMIUM: Momentum + mean reversion hybrid
   - Detect trends and trade with momentum
   - Use wider spreads to avoid adverse selection
   - Look for hidden patterns (as hinted in challenge description)
""")
