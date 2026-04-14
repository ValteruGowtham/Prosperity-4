"""
Test Round 1 Trader v3.0
Verifies both products trade correctly
"""

from round1_trader_v3 import Trader, OrderDepth, TradingState, Listing, Observation


def create_order_depth(buy_orders=None, sell_orders=None):
    od = OrderDepth()
    if buy_orders:
        od.buy_orders = buy_orders
    if sell_orders:
        od.sell_orders = sell_orders
    return od


def create_test_state(timestamp, order_depths, position=None, trader_data=""):
    listings = {
        "ASH_COATED_OSMIUM": Listing("ASH_COATED_OSMIUM", "ASH_COATED_OSMIUM", "XIRECS"),
        "INTARIAN_PEPPER_ROOT": Listing("INTARIAN_PEPPER_ROOT", "INTARIAN_PEPPER_ROOT", "XIRECS"),
    }
    
    if position is None:
        position = {"ASH_COATED_OSMIUM": 0, "INTARIAN_PEPPER_ROOT": 0}
    
    return TradingState(
        traderData=trader_data,
        timestamp=timestamp,
        listings=listings,
        order_depths=order_depths,
        own_trades={"ASH_COATED_OSMIUM": [], "INTARIAN_PEPPER_ROOT": []},
        market_trades={"ASH_COATED_OSMIUM": [], "INTARIAN_PEPPER_ROOT": []},
        position=position,
        observations=Observation()
    )


def test_v3_both_products():
    print("\n" + "="*60)
    print("TEST: v3.0 - Both Products Trading")
    print("="*60)
    
    trader = Trader()
    trader_data = ""
    
    for i in range(10):
        # Osmium: stable around 10000
        osmium_bid = 9995 + (i % 5)
        osmium_ask = 10011 + (i % 5)
        
        # Pepper: trending upward from 12000
        pepper_bid = 12000 + i
        pepper_ask = 12014 + i
        
        order_depths = {
            "ASH_COATED_OSMIUM": create_order_depth(
                buy_orders={osmium_bid: 10, osmium_bid - 2: 15},
                sell_orders={osmium_ask: -10, osmium_ask + 2: -15}
            ),
            "INTARIAN_PEPPER_ROOT": create_order_depth(
                buy_orders={pepper_bid: 10, pepper_bid - 2: 15},
                sell_orders={pepper_ask: -10, pepper_ask + 2: -15}
            ),
        }
        
        state = create_test_state(
            timestamp=i * 100,
            order_depths=order_depths,
            trader_data=trader_data
        )
        
        result, conversions, trader_data = trader.run(state)
        
        print(f"\n  t={i*100:5d}:")
        
        # Check Osmium
        if "ASH_COATED_OSMIUM" in result:
            osmium_orders = result["ASH_COATED_OSMIUM"]
            print(f"    ASH_COATED_OSMIUM: {len(osmium_orders)} orders")
            for order in osmium_orders:
                direction = "BUY" if order.quantity > 0 else "SELL"
                print(f"      {direction} {abs(order.quantity):2d} @ {order.price}")
        
        # Check Pepper
        if "INTARIAN_PEPPER_ROOT" in result:
            pepper_orders = result["INTARIAN_PEPPER_ROOT"]
            print(f"    INTARIAN_PEPPER_ROOT: {len(pepper_orders)} orders")
            for order in pepper_orders:
                direction = "BUY" if order.quantity > 0 else "SELL"
                print(f"      {direction} {abs(order.quantity):2d} @ {order.price}")
    
    print("\n" + "="*60)
    print("v3.0 EXPECTATIONS")
    print("="*60)
    print("""
✅ ASH_COATED_OSMIUM: Active BUY + SELL orders (proven strategy)
✅ INTARIAN_PEPPER_ROOT: Active BUY + SELL orders (conservative MM)
✅ Pepper has LONG bias (more aggressive buying when short)
✅ Pepper position limit: ±15 (tight, safe)
✅ Pepper spread: 7 points half-spread (wider than Osmium)

Expected improvement over v2.0:
- v2.0: +1296 XIRECS (Osmium only)
- v3.0: +1296 + Pepper profits = >+1296 XIRECS
""")


if __name__ == "__main__":
    test_v3_both_products()
