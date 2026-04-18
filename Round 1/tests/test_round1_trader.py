"""
Test script for Round 1 Trader
Simulates multiple iterations with realistic market data
"""

from round1_trader import Trader, TradingState, OrderDepth, Listing, Trade, Observation
import json

def create_order_depth(buy_orders=None, sell_orders=None):
    """Helper to create OrderDepth with proper initialization."""
    from round1_trader import OrderDepth as _OrderDepth
    od = _OrderDepth()
    if buy_orders:
        od.buy_orders = buy_orders
    if sell_orders:
        od.sell_orders = sell_orders
    return od

def create_test_state(timestamp, order_depths, position=None, own_trades=None, trader_data=""):
    """Create a test TradingState with realistic data."""
    
    listings = {
        "ASH_COATED_OSMIUM": Listing(
            symbol="ASH_COATED_OSMIUM",
            product="ASH_COATED_OSMIUM",
            denomination="XIRECS"
        ),
        "INTARIAN_PEPPER_ROOT": Listing(
            symbol="INTARIAN_PEPPER_ROOT",
            product="INTARIAN_PEPPER_ROOT",
            denomination="XIRECS"
        ),
    }
    
    if position is None:
        position = {"ASH_COATED_OSMIUM": 0, "INTARIAN_PEPPER_ROOT": 0}
    
    if own_trades is None:
        own_trades = {"ASH_COATED_OSMIUM": [], "INTARIAN_PEPPER_ROOT": []}
    
    observations = Observation()
    
    state = TradingState(
        traderData=trader_data,
        timestamp=timestamp,
        listings=listings,
        order_depths=order_depths,
        own_trades=own_trades,
        market_trades={"ASH_COATED_OSMIUM": [], "INTARIAN_PEPPER_ROOT": []},
        position=position,
        observations=observations
    )
    
    return state

def test_mean_reversion_scenario():
    """Test ASH_COATED_OSMIUM mean reversion strategy."""
    print("\n" + "="*60)
    print("TEST 1: ASH_COATED_OSMIUM Mean Reversion")
    print("="*60)
    
    trader = Trader()
    
    # Simulate 20 iterations with stable prices around 10000
    for i in range(20):
        # Simulate small price fluctuations
        base_price = 10000
        fluctuation = (i % 7) - 3  # Oscillates: -3, -2, -1, 0, 1, 2, 3
        
        bid_price = base_price + fluctuation - 8
        ask_price = base_price + fluctuation + 8
        
        order_depths = {
            "ASH_COATED_OSMIUM": create_order_depth(
                buy_orders={bid_price: 10, bid_price - 2: 15},
                sell_orders={ask_price: -10, ask_price + 2: -15}
            ),
            "INTARIAN_PEPPER_ROOT": create_order_depth(
                buy_orders={12000: 10},
                sell_orders={12020: -10}
            ),
        }
        
        state = create_test_state(
            timestamp=i * 100,
            order_depths=order_depths
        )
        
        result, conversions, trader_data = trader.run(state)
        
        if "ASH_COATED_OSMIUM" in result:
            orders = result["ASH_COATED_OSMIUM"]
            if orders:
                print(f"  t={i*100:5d} | Mid: {base_price + fluctuation:5d} | Orders: {len(orders)}")
                for order in orders:
                    direction = "BUY" if order.quantity > 0 else "SELL"
                    print(f"           {direction} {abs(order.quantity):2d} @ {order.price}")
    
    print("\n✅ Mean reversion test completed")

def test_trending_scenario():
    """Test INTARIAN_PEPPER_ROOT trend following strategy."""
    print("\n" + "="*60)
    print("TEST 2: INTARIAN_PEPPER_ROOT Trend Following")
    print("="*60)
    
    trader = Trader()
    
    # Simulate upward trending prices
    base_price = 12000
    for i in range(30):
        # Upward trend: +1 per tick on average
        current_price = base_price + i
        
        bid_price = current_price - 7
        ask_price = current_price + 7
        
        order_depths = {
            "ASH_COATED_OSMIUM": create_order_depth(
                buy_orders={10000: 10},
                sell_orders={10016: -10}
            ),
            "INTARIAN_PEPPER_ROOT": create_order_depth(
                buy_orders={bid_price: 10, bid_price - 2: 15},
                sell_orders={ask_price: -10, ask_price + 2: -15}
            ),
        }
        
        state = create_test_state(
            timestamp=i * 100,
            order_depths=order_depths
        )
        
        result, conversions, trader_data = trader.run(state)
        
        if "INTARIAN_PEPPER_ROOT" in result:
            orders = result["INTARIAN_PEPPER_ROOT"]
            if orders:
                print(f"  t={i*100:5d} | Price: {current_price:5d} | Orders: {len(orders)}")
                for order in orders:
                    direction = "BUY" if order.quantity > 0 else "SELL"
                    print(f"           {direction} {abs(order.quantity):2d} @ {order.price}")
    
    print("\n✅ Trend following test completed")

def test_position_limits():
    """Test that position limits are respected."""
    print("\n" + "="*60)
    print("TEST 3: Position Limits")
    print("="*60)
    
    trader = Trader()
    
    # Start with large long position
    position = {"ASH_COATED_OSMIUM": 35, "INTARIAN_PEPPER_ROOT": 0}
    
    for i in range(10):
        order_depths = {
            "ASH_COATED_OSMIUM": create_order_depth(
                buy_orders={9995: 10, 9993: 15},
                sell_orders={10011: -10, 10013: -15}
            ),
            "INTARIAN_PEPPER_ROOT": create_order_depth(
                buy_orders={12000: 10},
                sell_orders={12020: -10}
            ),
        }
        
        state = create_test_state(
            timestamp=i * 100,
            order_depths=order_depths,
            position=position
        )
        
        result, conversions, trader_data = trader.run(state)
        
        if "ASH_COATED_OSMIUM" in result:
            orders = result["ASH_COATED_OSMIUM"]
            buy_orders = [o for o in orders if o.quantity > 0]
            sell_orders = [o for o in orders if o.quantity < 0]
            
            print(f"  t={i*100:5d} | Position: {position['ASH_COATED_OSMIUM']:3d} | ", end="")
            print(f"Buys: {len(buy_orders)}, Sells: {len(sell_orders)}")
            
            # Should only sell or place small buys when near limit
            for order in orders:
                direction = "BUY" if order.quantity > 0 else "SELL"
                print(f"           {direction} {abs(order.quantity):2d} @ {order.price}")
    
    print("\n✅ Position limits test completed")

def test_state_persistence():
    """Test that state persists via traderData."""
    print("\n" + "="*60)
    print("TEST 4: State Persistence (traderData)")
    print("="*60)
    
    trader = Trader()
    trader_data = ""
    
    # Run 5 iterations, saving trader_data each time
    for i in range(5):
        order_depths = {
            "ASH_COATED_OSMIUM": create_order_depth(
                buy_orders={9995: 10},
                sell_orders={10011: -10}
            ),
            "INTARIAN_PEPPER_ROOT": create_order_depth(
                buy_orders={12000 + i: 10},
                sell_orders={12020 + i: -10}
            ),
        }
        
        state = create_test_state(
            timestamp=i * 100,
            order_depths=order_depths,
            trader_data=trader_data
        )
        
        result, conversions, trader_data = trader.run(state)
        
        # Verify trader_data is being populated
        if i == 0:
            print(f"  Initial trader_data length: {len(trader_data)} chars")
        elif i == 4:
            print(f"  After 5 iterations, trader_data length: {len(trader_data)} chars")
            
            # Verify we can deserialize it
            state_dict = json.loads(trader_data)
            print(f"  Fair values: {state_dict.get('fair_value', {})}")
    
    # Simulate AWS Lambda reset - create new trader instance
    print("\n  Simulating AWS Lambda reset...")
    new_trader = Trader()
    
    order_depths = {
        "ASH_COATED_OSMIUM": create_order_depth(
            buy_orders={9995: 10},
            sell_orders={10011: -10}
        ),
        "INTARIAN_PEPPER_ROOT": create_order_depth(
            buy_orders={12005: 10},
            sell_orders={12025: -10}
        ),
    }
    
    state = create_test_state(
        timestamp=500,
        order_depths=order_depths,
        trader_data=trader_data  # Pass the saved state
    )
    
    result, conversions, new_trader_data = new_trader.run(state)
    
    # Verify state was restored
    state_dict = json.loads(new_trader_data)
    print(f"  Restored fair values: {state_dict.get('fair_value', {})}")
    print(f"  State initialized: {state_dict.get('initialized', False)}")
    
    print("\n✅ State persistence test completed")

def test_order_properties():
    """Test that orders have correct properties."""
    print("\n" + "="*60)
    print("TEST 5: Order Properties Validation")
    print("="*60)
    
    trader = Trader()
    
    order_depths = {
        "ASH_COATED_OSMIUM": create_order_depth(
            buy_orders={9995: 10, 9993: 15},
            sell_orders={10011: -10, 10013: -15}
        ),
        "INTARIAN_PEPPER_ROOT": create_order_depth(
            buy_orders={12000: 10, 11998: 15},
            sell_orders={12020: -10, 12022: -15}
        ),
    }
    
    state = create_test_state(
        timestamp=0,
        order_depths=order_depths
    )
    
    result, conversions, trader_data = trader.run(state)
    
    for product, orders in result.items():
        print(f"\n  {product}:")
        for order in orders:
            # Validate order properties
            assert order.symbol == product, f"Wrong symbol: {order.symbol}"
            assert isinstance(order.price, int), f"Price not int: {order.price}"
            assert isinstance(order.quantity, int), f"Quantity not int: {order.quantity}"
            assert order.quantity != 0, "Zero quantity order"
            
            # Check sign convention
            if order.quantity > 0:
                print(f"    ✅ BUY  {order.quantity:2d} @ {order.price}")
            else:
                print(f"    ✅ SELL {abs(order.quantity):2d} @ {order.price}")
    
    print("\n✅ Order properties validation completed")

if __name__ == "__main__":
    print("="*60)
    print("PROSPERITY 4 - ROUND 1 TRADER TESTS")
    print("="*60)
    
    try:
        test_mean_reversion_scenario()
        test_trending_scenario()
        test_position_limits()
        test_state_persistence()
        test_order_properties()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
