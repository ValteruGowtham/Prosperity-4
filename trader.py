"""
Prosperity 4 - Algorithmic Trading Bot v2.0
Strategy: Conservative Mean-Reversion Market Maker

Improvements over v1:
- Passive market making (earn spread, don't pay it)
- Minimum deviation threshold before trading
- Reduced order sizes to limit drawdowns
- Momentum filter to avoid trading against trends
- Inventory-aware quote skewing
"""

from typing import Dict, List, Optional, Tuple
from collections import deque


# ============================================================
# Data Model Classes (match platform's datamodel.py)
# ============================================================
class Order:
    def __init__(self, symbol: str, price: int, quantity: int) -> None:
        self.symbol = symbol
        self.price = price
        self.quantity = quantity

    def __str__(self) -> str:
        return f"({self.symbol}, {self.price}, {self.quantity})"

    def __repr__(self) -> str:
        return f"({self.symbol}, {self.price}, {self.quantity})"


class OrderDepth:
    def __init__(self):
        self.buy_orders: Dict[int, int] = {}
        self.sell_orders: Dict[int, int] = {}


class Trade:
    def __init__(self, symbol: str, price: int, quantity: int,
                 buyer: str = None, seller: str = None, timestamp: int = 0) -> None:
        self.symbol = symbol
        self.price = price
        self.quantity = quantity
        self.buyer = buyer
        self.seller = seller
        self.timestamp = timestamp


class Listing:
    def __init__(self, symbol: str, product: str, denomination: str):
        self.symbol = symbol
        self.product = product
        self.denomination = denomination


class Observation:
    def __init__(self):
        self.plainValueObservations: Dict = {}
        self.conversionObservations: Dict = {}


class TradingState:
    def __init__(self,
                 traderData: str,
                 timestamp: int,
                 listings: Dict[str, Listing],
                 order_depths: Dict[str, OrderDepth],
                 own_trades: Dict[str, List[Trade]],
                 market_trades: Dict[str, List[Trade]],
                 position: Dict[str, int],
                 observations: Observation):
        self.traderData = traderData
        self.timestamp = timestamp
        self.listings = listings
        self.order_depths = order_depths
        self.own_trades = own_trades
        self.market_trades = market_trades
        self.position = position
        self.observations = observations


# ============================================================
# Product Configuration
# ============================================================
PRODUCT_CONFIG = {
    "EMERALDS": {
        "fair_value_default": 10000,
        "target_half_spread": 5,       # Tighter spread for stability
        "order_size": 5,               # Reduced from 8
        "max_position": 20,            # Reduced from 30 for safety
        "min_deviation_pct": 0.0008,   # Only trade if price deviates 0.08%+
        "volatility_lookback": 10,
        "fair_value_window": 15,
    },
    "TOMATOES": {
        "fair_value_default": 5000,
        "target_half_spread": 5,       # Tighter spread
        "order_size": 3,               # Reduced from 5
        "max_position": 15,            # Reduced from 25 for safety
        "min_deviation_pct": 0.0012,   # Higher threshold for volatile product
        "volatility_lookback": 10,
        "fair_value_window": 15,
    },
}

# Global settings
INVENTORY_SKEW_FACTOR = 0.3    # Reduced from 0.5 - less aggressive skew
MOMENTUM_WINDOW = 5            # Look back 5 periods for momentum
MOMENTUM_THRESHOLD = 0.0003    # Skip trading if momentum too strong against us


# ============================================================
# Product Tracker - tracks state per product
# ============================================================
class ProductTracker:
    """Tracks price history, fair value, and momentum for a single product."""

    def __init__(self, config: dict):
        self.config = config
        self.mid_prices: deque = deque(maxlen=config["fair_value_window"])
        self.fair_value: float = float(config["fair_value_default"])
        self.recent_mids: deque = deque(maxlen=MOMENTUM_WINDOW)

    def update(self, mid_price: int) -> dict:
        """Update tracker with new mid price. Returns analysis dict."""
        self.mid_prices.append(mid_price)
        self.recent_mids.append(mid_price)

        # Calculate fair value as median of recent prices
        fair_value = self._calculate_fair_value()

        # Calculate momentum (recent price direction)
        momentum = self._calculate_momentum()

        # Calculate volatility
        volatility = self._calculate_volatility()

        return {
            "fair_value": fair_value,
            "momentum": momentum,
            "volatility": volatility,
            "mid_price": mid_price,
        }

    def _calculate_fair_value(self) -> float:
        if len(self.mid_prices) < 3:
            return self.fair_value

        sorted_prices = sorted(self.mid_prices)
        n = len(sorted_prices)
        if n % 2 == 0:
            self.fair_value = (sorted_prices[n // 2 - 1] + sorted_prices[n // 2]) / 2
        else:
            self.fair_value = sorted_prices[n // 2]
        return self.fair_value

    def _calculate_momentum(self) -> float:
        """Returns momentum: positive = price rising, negative = price falling."""
        if len(self.recent_mids) < 3:
            return 0.0

        recent = list(self.recent_mids)
        # Compare first half to second half
        half = len(recent) // 2
        first_avg = sum(recent[:half]) / half
        second_avg = sum(recent[half:]) / (len(recent) - half)

        if first_avg == 0:
            return 0.0

        return (second_avg - first_avg) / first_avg

    def _calculate_volatility(self) -> float:
        """Returns average absolute return over recent periods."""
        if len(self.mid_prices) < 3:
            return 0.0

        prices = list(self.mid_prices)
        returns = []
        for i in range(1, len(prices)):
            if prices[i - 1] != 0:
                ret = abs(prices[i] - prices[i - 1]) / prices[i - 1]
                returns.append(ret)

        return sum(returns) / len(returns) if returns else 0.0


# ============================================================
# Trader Class
# ============================================================
class Trader:
    def __init__(self):
        self.trackers: Dict[str, ProductTracker] = {}

    def bid(self):
        return 15

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        """Main trading method called by the platform each iteration."""
        result: Dict[str, List[Order]] = {}

        # Initialize trackers for any new products
        for product in state.order_depths:
            if product not in self.trackers and product in PRODUCT_CONFIG:
                self.trackers[product] = ProductTracker(PRODUCT_CONFIG[product])

        position = state.position

        for product in state.order_depths:
            if product not in PRODUCT_CONFIG:
                continue

            config = PRODUCT_CONFIG[product]
            tracker = self.trackers[product]
            order_depth: OrderDepth = state.order_depths[product]
            current_position = position.get(product, 0)

            # Calculate mid price
            mid_price = self._get_mid_price(order_depth)
            if mid_price is None:
                # No valid order book, skip
                result[product] = []
                continue

            # Update tracker and get analysis
            analysis = tracker.update(mid_price)
            fair_value = analysis["fair_value"]
            momentum = analysis["momentum"]
            volatility = analysis["volatility"]

            # === DECISION LOGIC ===

            # 1. Check if price deviation is significant enough
            deviation = (fair_value - mid_price) / fair_value if fair_value > 0 else 0
            abs_deviation = abs(deviation)
            min_dev = config["min_deviation_pct"]

            # 2. Check momentum - don't trade against strong momentum
            should_trade = True
            if abs(momentum) > MOMENTUM_THRESHOLD:
                # Momentum is strong - only trade if it supports our direction
                if deviation > 0 and momentum < -MOMENTUM_THRESHOLD:
                    # Price below fair value (want to buy) but falling fast
                    should_trade = False
                elif deviation < 0 and momentum > MOMENTUM_THRESHOLD:
                    # Price above fair value (want to sell) but rising fast
                    should_trade = False

            # 3. Calculate optimal quotes with all adjustments
            orders = self._calculate_orders(
                product=product,
                config=config,
                order_depth=order_depth,
                fair_value=fair_value,
                mid_price=mid_price,
                deviation=deviation,
                current_position=current_position,
                should_trade=should_trade,
                abs_deviation=abs_deviation,
                min_dev=min_dev,
            )

            result[product] = orders

        trader_data = ""
        conversions = 0
        return result, conversions, trader_data

    def _get_mid_price(self, order_depth: OrderDepth) -> Optional[int]:
        """Calculate mid price from order book."""
        if order_depth.buy_orders and order_depth.sell_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            return (best_bid + best_ask) // 2
        return None

    def _calculate_orders(
        self,
        product: str,
        config: dict,
        order_depth: OrderDepth,
        fair_value: float,
        mid_price: int,
        deviation: float,
        current_position: int,
        should_trade: bool,
        abs_deviation: float,
        min_dev: float,
    ) -> List[Order]:
        """Calculate orders based on market conditions."""
        orders: List[Order] = []
        max_position = config["max_position"]
        order_size = config["order_size"]
        base_half_spread = config["target_half_spread"]

        # --- Strategy: Passive Market Making ---
        # We place orders INSIDE the spread to earn it, not at the edges.
        # Only adjust our fair value estimate significantly if deviation is large.

        # Calculate inventory skew
        if max_position > 0:
            inventory_ratio = current_position / max_position
        else:
            inventory_ratio = 0

        # Adjust spread for volatility (wider in volatile markets)
        vol_multiplier = 1.0 + (abs_deviation * 100)  # Small adjustment
        adjusted_spread = base_half_spread * vol_multiplier

        # Inventory skew: shift quotes to reduce position
        skew = inventory_ratio * INVENTORY_SKEW_FACTOR * adjusted_spread

        # Calculate our passive bid and ask
        our_bid = int(fair_value - adjusted_spread + skew)
        our_ask = int(fair_value + adjusted_spread + skew)

        # Ensure minimum spread of 2
        if our_ask - our_bid < 2:
            midpoint = (our_bid + our_ask) // 2
            our_bid = midpoint - 1
            our_ask = midpoint + 1

        # Clip prices to be within current spread (don't cross the market)
        if order_depth.buy_orders and order_depth.sell_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())

            # Our bid should be <= best_ask - 1 (don't cross)
            our_bid = min(our_bid, best_ask - 1)
            # Our ask should be >= best_bid + 1 (don't cross)
            our_ask = max(our_ask, best_bid + 1)

            # If deviation is significant, we can be more aggressive
            # and place orders closer to mid price
            if abs_deviation >= min_dev and should_trade:
                if deviation > 0:
                    # Price is below fair value - more aggressive bid
                    aggressive_bid = int(fair_value - adjusted_spread * 0.5 + skew)
                    our_bid = max(our_bid, aggressive_bid)
                elif deviation < 0:
                    # Price is above fair value - more aggressive ask
                    aggressive_ask = int(fair_value + adjusted_spread * 0.5 + skew)
                    our_ask = min(our_ask, aggressive_ask)

        # Place buy order if we have room
        if current_position < max_position:
            buy_qty = min(order_size, max_position - current_position)
            if buy_qty > 0:
                orders.append(Order(product, our_bid, buy_qty))

        # Place sell order if we have room
        if current_position > -max_position:
            sell_qty = min(order_size, max_position + current_position)
            if sell_qty > 0:
                orders.append(Order(product, our_ask, -sell_qty))

        return orders
