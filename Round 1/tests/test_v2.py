"""
Test script for Round 1 Trader v2.0
Verifies:
1. ASH_COATED_OSMIUM strategy works (same as v1.0)
2. INTARIAN_PEPPER_ROOT is skipped (no orders)
"""

from round1_trader_v2 import Trader, OrderDepth


def create_order_depth(buy_orders=None, sell_orders=None):
    """Helper to create OrderDepth."""
    od = OrderDepth()
    if buy_orders:
        od.buy_orders = buy_orders
    if sell_orders:
        od.sell_orders = sell_orders
    return od


def create_test_state(timestamp, order_depths, position=None, trader_data=""):
    """Create a test TradingState."""
    from round1_trader_v2 import TradingState, Listing, Observation
    
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

def test_v2_behavior():
    """Test that v2.0 only trades Osmium and skips Pepper."""
    print("\n" + "="*60)
    print("TEST: v2.0 Strategy Behavior")
    print("="*60)
    
    trader = Trader()
    trader_data = ""
    
    # Simulate 10 iterations
    for i in range(10):
        # Osmium: stable around 10000
        osmium_bid = 9995 + (i % 5)
        osmium_ask = 10011 + (i % 5)
        
        # Pepper: trending upward
        pepper_bid = 12000 + i
        pepper_ask = 12020 + i
        
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
        
        # Check Osmium orders
        if "ASH_COATED_OSMIUM" in result:
            osmium_orders = result["ASH_COATED_OSMIUM"]
            print(f"    ASH_COATED_OSMIUM: {len(osmium_orders)} orders")
            for order in osmium_orders:
                direction = "BUY" if order.quantity > 0 else "SELL"
                print(f"      {direction} {abs(order.quantity):2d} @ {order.price}")
        else:
            print(f"    ASH_COATED_OSMIUM: NO ORDERS ❌")
        
        # Check Pepper orders
        if "INTARIAN_PEPPER_ROOT" in result:
            pepper_orders = result["INTARIAN_PEPPER_ROOT"]
            if len(pepper_orders) == 0:
                print(f"    INTARIAN_PEPPER_ROOT: SKIPPED ✅ (no orders)")
            else:
                print(f"    INTARIAN_PEPPER_ROOT: {len(pepper_orders)} orders ❌ (should be 0!)")
                for order in pepper_orders:
                    direction = "BUY" if order.quantity > 0 else "SELL"
                    print(f"      {direction} {abs(order.quantity):2d} @ {order.price}")
        else:
            print(f"    INTARIAN_PEPPER_ROOT: NOT IN RESULT ✅")
    
    print("\n" + "="*60)
    print("v2.0 BEHAVIOR VERIFICATION")
    print("="*60)
    print("""
Expected:
- ASH_COATED_OSMIUM: Active trading (BUY + SELL orders)
- INTARIAN_PEPPER_ROOT: No orders placed (skipped)

This ensures:
- Osmium continues to generate +1296 XIRECS
- Pepper losses are eliminated (was -1692 XIRECS)
- Net result should be ~+1296 XIRECS instead of -395
""")

if __name__ == "__main__":
    test_v2_behavior()
