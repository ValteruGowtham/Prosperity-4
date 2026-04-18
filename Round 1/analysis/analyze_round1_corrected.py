"""
Round 1 Data Analysis - Corrected (filtering out missing data)
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
        'timestamps': [],
    })
    
    with open(filename, 'r') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            product = row['product']
            mid_price = float(row['mid_price'])
            timestamp = int(row['timestamp'])
            
            # Skip rows where mid_price is 0 (missing data)
            if mid_price == 0:
                continue
            
            # Only record if we have valid bid/ask
            bid1 = float(row['bid_price_1']) if row['bid_price_1'] else None
            ask1 = float(row['ask_price_1']) if row['ask_price_1'] else None
            
            products[product]['mid_prices'].append(mid_price)
            products[product]['timestamps'].append(timestamp)
            
            if bid1 and ask1:
                spread = ask1 - bid1
                products[product]['spreads'].append(spread)
                products[product]['bid_prices'].append(bid1)
                products[product]['ask_prices'].append(ask1)
    
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

def calculate_autocorrelation(series, lag):
    """Calculate autocorrelation for a given lag."""
    n = len(series)
    if n <= lag:
        return 0
    
    mean = statistics.mean(series)
    var = sum((x - mean)**2 for x in series) / n
    
    if var == 0:
        return 0
    
    cov = sum((series[i] - mean) * (series[i+lag] - mean) for i in range(n - lag)) / (n - lag)
    return cov / var

def print_product_stats(product_name, price_data, trades_data=None):
    """Print comprehensive statistics for a product."""
    mid_prices = price_data['mid_prices']
    timestamps = price_data['timestamps']
    
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
    positive_changes = [c for c in price_changes if c > 0]
    negative_changes = [c for c in price_changes if c < 0]
    
    print(f"\n📈 Price Changes (tick-to-tick):")
    print(f"  Mean change: {statistics.mean(price_changes):.4f}")
    print(f"  Std Dev of changes: {statistics.stdev(price_changes):.4f}")
    print(f"  Positive changes: {len(positive_changes)} (avg: {statistics.mean(positive_changes):.2f})")
    print(f"  Negative changes: {len(negative_changes)} (avg: {statistics.mean(negative_changes):.2f})")
    
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
        trade_timestamps = trades_data['timestamps']
        
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
        if len(trade_timestamps) > 1:
            time_diffs = [trade_timestamps[i+1] - trade_timestamps[i] for i in range(len(trade_timestamps)-1)]
            print(f"\n⏱️  Trade Frequency:")
            print(f"  Mean time between trades: {statistics.mean(time_diffs):.1f} ms")
            print(f"  Median time between trades: {statistics.median(time_diffs):.1f} ms")
    
    # Autocorrelation analysis
    if len(mid_prices) > 100:
        print(f"\n🔍 Autocorrelation (price momentum):")
        for lag in [1, 5, 10, 50, 100]:
            autocorr = calculate_autocorrelation(mid_prices, lag)
            print(f"  Lag {lag}: {autocorr:.4f}")
    
    # Mean reversion analysis
    if len(mid_prices) > 50:
        print(f"\n🔄 Mean Reversion Analysis:")
        window = 50
        reversion_count = 0
        total_crossings = 0
        
        for i in range(window, len(mid_prices) - 1):
            rolling_mean = statistics.mean(mid_prices[i-window:i])
            curr = mid_prices[i]
            next_price = mid_prices[i+1]
            
            # Check if price crossed back toward mean
            if curr > rolling_mean and next_price < curr:
                reversion_count += 1
                total_crossings += 1
            elif curr < rolling_mean and next_price > curr:
                reversion_count += 1
                total_crossings += 1
            elif (curr > rolling_mean and next_price > curr) or (curr < rolling_mean and next_price < curr):
                total_crossings += 1
        
        if total_crossings > 0:
            reversion_rate = reversion_count / total_crossings
            print(f"  Mean reversion rate: {reversion_rate:.2%}")
            print(f"  (0.5 = random, >0.5 = mean reverting, <0.5 = trending)")
    
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
print("PROSPERITY 4 - ROUND 1 DEEP DATA ANALYSIS (CORRECTED)")
print("="*60)

all_stats = {'ASH_COATED_OSMIUM': [], 'INTARIAN_PEPPER_ROOT': []}

for day_file, trades_file in zip(days, trades_files):
    print(f"\n\n{'#'*60}")
    print(f"# Analyzing Day: {day_file.replace('prices_', '').replace('.csv', '').upper()}")
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
    
    print(f"  Mean of daily means: {statistics.mean(means):.2f}")
    print(f"  Mean of daily stds: {statistics.mean(stds):.2f}")
    print(f"  Overall range: {min(mins):.2f} to {max(maxs):.2f}")
    if len(means) > 1:
        print(f"  Day-to-day variation (std of means): {statistics.stdev(means):.2f}")

print(f"\n{'='*60}")
print("KEY INSIGHTS & ALGORITHM RECOMMENDATIONS")
print(f"{'='*60}")
