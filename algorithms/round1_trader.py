"""
Prosperity 4 - Round 1 Trading Algorithm
Products: ASH_COATED_OSMIUM, INTARIAN_PEPPER_ROOT

Strategy based on deep data analysis:

ASH_COATED_OSMIUM:
- VERY stable: trades in tight range ~10000 ±20 (std=5.12)
- Mean reversion rate: ~69% (strong mean reversion)
- Autocorrelation decays quickly (lag-100: 0.57)
- Spread: ~16 points
- Strategy: Market making with tight spreads

INTARIAN_PEPPER_ROOT:
- STRONG upward trend: autocorrelation ~0.999 (nearly perfect)
- Mean price drifts upward ~1000 points per day
- Mean reversion rate: ~51% (barely mean reverting - essentially trending)
- Day-to-day variation: std of 1000 points
- Spread: ~12-14 points
- Strategy: Trend-following with wider stops
"""

import json
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
# Product Configuration (based on data analysis)
# ============================================================
PRODUCT_CONFIG = {
    "ASH_COATED_OSMIUM": {
        # Extremely stable, mean-reverting
        "fair_value_default": 10000,
        "target_half_spread": 4,       # Tight: product is very stable
        "order_size": 10,              # Can go larger - very stable
        "max_position": 40,            # Half of 80 limit - conservative
        "min_deviation_pct": 0.0003,   # Very low threshold - trade often
        "ema_alpha": 0.05,             # Slow adaptation (very stable)
        "strategy": "mean_reversion",  # Pure market making
    },
    "INTARIAN_PEPPER_ROOT": {
        # Strong upward trend, barely mean-reverting
        "fair_value_default": 12000,   # Will be updated dynamically
        "target_half_spread": 6,       # Wider: trending product
        "order_size": 8,               # Moderate size
        "max_position": 40,            # Half of 80 limit
        "min_deviation_pct": 0.001,    # Higher threshold - be selective
        "ema_alpha": 0.2,              # Fast adaptation (trending)
        "strategy": "trend_following", # Follow the trend
        "trend_window": 100,           # For trend detection
    },
}

# Global settings
INVENTORY_SKEW_FACTOR = 0.3
MOMENTUM_WINDOW = 10
MOMENTUM_THRESHOLD_OSMIUM = 0.0002   # Very low - Osmium mean-reverts strongly
MOMENTUM_THRESHOLD_PEPPER = 0.001    # Higher - Pepper trends


# ============================================================
# State Management (serialized via traderData)
# ============================================================
class SerializableState:
    """All state that must persist across Lambda invocations."""

    def __init__(self):
        # EMA-based fair value per product
        self.fair_value: Dict[str, float] = {}
        # Price history for momentum/trend calculation
        self.price_history: Dict[str, List[float]] = {}
        # Internal position tracker
        self.internal_position: Dict[str, int] = {}
        # Last known timestamp
        self.last_timestamp: int = 0
        # Trend slope for INTARIAN_PEPPER_ROOT
        self.trend_slope: Dict[str, float] = {}
        # Initialization flag
        self.initialized: bool = False

    def to_dict(self) -> dict:
        return {
            "fair_value": self.fair_value,
            "price_history": self.price_history,
            "internal_position": self.internal_position,
            "last_timestamp": self.last_timestamp,
            "trend_slope": self.trend_slope,
            "initialized": self.initialized,
        }

    @staticmethod
    def from_dict(data: dict) -> "SerializableState":
        state = SerializableState()
        state.fair_value = data.get("fair_value", {})
        state.price_history = data.get("price_history", {})
        state.internal_position = data.get("internal_position", {})
        state.last_timestamp = data.get("last_timestamp", 0)
        state.trend_slope = data.get("trend_slope", {})
        state.initialized = data.get("initialized", False)
        return state

    def serialize(self) -> str:
        return json.dumps(self.to_dict())

    @staticmethod
    def deserialize(data: str) -> "SerializableState":
        if not data or data.strip() == "":
            return SerializableState()
        try:
            return SerializableState.from_dict(json.loads(data))
        except (json.JSONDecodeError, KeyError):
            return SerializableState()


# ============================================================
# Trader Class - Round 1
# ============================================================
class Trader:
    def __init__(self):
        self.state = SerializableState()
        self._initialized = False

    def bid(self):
        return 15

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        """Main trading method called by the platform each iteration."""

        # === Restore state from traderData (AWS Lambda is stateless) ===
        if not self._initialized:
            self.state = SerializableState.deserialize(state.traderData)
            self._initialized = True

        # Detect if we've been reset
        if state.timestamp < self.state.last_timestamp:
            # Keep fair_value and positions but reset short-term history
            self.state.price_history = {}

        result: Dict[str, List[Order]] = {}

        # === Update positions from own_trades ===
        self._update_positions(state)

        # === Process each product ===
        for product in state.order_depths:
            if product not in PRODUCT_CONFIG:
                continue

            config = PRODUCT_CONFIG[product]
            order_depth: OrderDepth = state.order_depths[product]

            # Get current position
            current_position = state.position.get(
                product, self.state.internal_position.get(product, 0))

            # Calculate mid price
            mid_price = self._get_mid_price(order_depth)
            if mid_price is None:
                result[product] = []
                continue

            # Update fair value using EMA
            fair_value = self._update_fair_value(product, mid_price, config)

            # Calculate momentum/trend
            momentum = self._calculate_momentum(product, mid_price, config)

            # Generate orders based on product-specific strategy
            if config["strategy"] == "mean_reversion":
                orders = self._mean_reversion_orders(
                    product=product,
                    config=config,
                    order_depth=order_depth,
                    fair_value=fair_value,
                    mid_price=mid_price,
                    current_position=current_position,
                    momentum=momentum,
                )
            elif config["strategy"] == "trend_following":
                orders = self._trend_following_orders(
                    product=product,
                    config=config,
                    order_depth=order_depth,
                    fair_value=fair_value,
                    mid_price=mid_price,
                    current_position=current_position,
                    momentum=momentum,
                )
            else:
                orders = []

            result[product] = orders

        # === Save state for next invocation ===
        self.state.last_timestamp = state.timestamp
        trader_data = self.state.serialize()
        conversions = 0

        return result, conversions, trader_data

    def _update_positions(self, state: TradingState):
        """Update internal position tracker from own_trades."""
        for product, trades in state.own_trades.items():
            if product not in self.state.internal_position:
                self.state.internal_position[product] = 0

            for trade in trades:
                if trade.buyer == "SUBMISSION":
                    self.state.internal_position[product] += trade.quantity
                elif trade.seller == "SUBMISSION":
                    self.state.internal_position[product] -= trade.quantity

    def _get_mid_price(self, order_depth: OrderDepth) -> Optional[int]:
        """Calculate mid price from order book."""
        if order_depth.buy_orders and order_depth.sell_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            return (best_bid + best_ask) // 2
        return None

    def _update_fair_value(self, product: str, mid_price: int, config: dict) -> float:
        """Update EMA-based fair value."""
        alpha = config["ema_alpha"]

        if product not in self.state.fair_value:
            self.state.fair_value[product] = float(mid_price)
            return self.state.fair_value[product]

        old_fv = self.state.fair_value[product]
        new_fv = alpha * mid_price + (1 - alpha) * old_fv
        self.state.fair_value[product] = new_fv

        return new_fv

    def _calculate_momentum(self, product: str, mid_price: int, config: dict) -> float:
        """Calculate momentum from recent price history."""
        if product not in self.state.price_history:
            self.state.price_history[product] = []

        history = self.state.price_history[product]
        history.append(float(mid_price))

        # Keep last N prices
        window = MOMENTUM_WINDOW
        if product == "INTARIAN_PEPPER_ROOT":
            window = config.get("trend_window", 100)

        if len(history) > window:
            self.state.price_history[product] = history[-window:]
            history = self.state.price_history[product]

        if len(history) < 3:
            return 0.0

        # Calculate trend slope using linear regression (simplified)
        n = len(history)
        half = n // 2
        first_avg = sum(history[:half]) / half
        second_avg = sum(history[half:]) / (n - half)

        if first_avg == 0:
            return 0.0

        momentum = (second_avg - first_avg) / first_avg

        # For INTARIAN_PEPPER_ROOT, also track trend slope
        if product == "INTARIAN_PEPPER_ROOT" and n > 10:
            # Simple linear regression slope
            x_mean = (n - 1) / 2
            y_mean = sum(history) / n
            numerator = sum((i - x_mean) * (history[i] - y_mean) for i in range(n))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            if denominator > 0:
                slope = numerator / denominator
                self.state.trend_slope[product] = slope

        return momentum

    def _mean_reversion_orders(
        self,
        product: str,
        config: dict,
        order_depth: OrderDepth,
        fair_value: float,
        mid_price: int,
        current_position: int,
        momentum: float,
    ) -> List[Order]:
        """Market making for mean-reverting product (ASH_COATED_OSMIUM).
        
        Strategy: Place passive orders around fair value, earn the spread.
        Product is VERY stable (std=5), so we can be aggressive.
        """
        orders: List[Order] = []
        max_position = config["max_position"]
        order_size = config["order_size"]
        base_half_spread = config["target_half_spread"]

        # === Deviation check ===
        deviation = (fair_value - mid_price) / fair_value if fair_value > 0 else 0
        abs_deviation = abs(deviation)
        min_dev = config["min_deviation_pct"]

        # === Momentum filter (relaxed for mean-reverting product) ===
        # Only block trades if momentum is VERY strong against us
        momentum_threshold = MOMENTUM_THRESHOLD_OSMIUM
        should_trade = True
        if abs(momentum) > momentum_threshold:
            # Strong momentum against our position
            if deviation > 0 and momentum < -momentum_threshold * 2:
                should_trade = False  # Price falling, don't buy
            elif deviation < 0 and momentum > momentum_threshold * 2:
                should_trade = False  # Price rising, don't sell

        # === Inventory skew ===
        if max_position > 0:
            inventory_ratio = current_position / max_position
        else:
            inventory_ratio = 0

        # === Volatility adjustment (minimal for stable product) ===
        vol_multiplier = 1.0 + (abs_deviation * 20)  # Very light adjustment
        adjusted_spread = base_half_spread * vol_multiplier

        # === Skew calculation ===
        skew = inventory_ratio * INVENTORY_SKEW_FACTOR * adjusted_spread

        # === Calculate optimal bid/ask ===
        our_bid = int(fair_value - adjusted_spread + skew)
        our_ask = int(fair_value + adjusted_spread + skew)

        # Ensure minimum spread of 2
        if our_ask - our_bid < 2:
            midpoint = (our_bid + our_ask) // 2
            our_bid = midpoint - 1
            our_ask = midpoint + 1

        # Don't cross the market
        if order_depth.buy_orders and order_depth.sell_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            
            # Ensure we're inside the spread (passive market making)
            if our_bid >= best_ask:
                our_bid = best_ask - 1
            if our_ask <= best_bid:
                our_ask = best_bid + 1

            # Place aggressive orders only if deviation is significant
            if abs_deviation >= min_dev and should_trade:
                if deviation > 0:
                    # Price below fair value - bid aggressively
                    aggressive_bid = int(fair_value - adjusted_spread * 0.2 + skew)
                    our_bid = max(our_bid, min(aggressive_bid, best_ask - 1))
                elif deviation < 0:
                    # Price above fair value - ask aggressively
                    aggressive_ask = int(fair_value + adjusted_spread * 0.2 + skew)
                    our_ask = min(our_ask, max(aggressive_ask, best_bid + 1))

        # === Place orders ===
        if current_position < max_position:
            buy_qty = min(order_size, max_position - current_position)
            if buy_qty > 0:
                orders.append(Order(product, our_bid, buy_qty))

        if current_position > -max_position:
            sell_qty = min(order_size, max_position + current_position)
            if sell_qty > 0:
                orders.append(Order(product, our_ask, -sell_qty))

        return orders

    def _trend_following_orders(
        self,
        product: str,
        config: dict,
        order_depth: OrderDepth,
        fair_value: float,
        mid_price: int,
        current_position: int,
        momentum: float,
    ) -> List[Order]:
        """Trend following for INTARIAN_PEPPER_ROOT.
        
        Strategy: This product trends UPWARD with autocorrelation ~0.999
        - Bias toward LONG positions
        - Use wider spreads to avoid getting run over
        - Follow the trend direction
        """
        orders: List[Order] = []
        max_position = config["max_position"]
        order_size = config["order_size"]
        base_half_spread = config["target_half_spread"]

        # === Get trend slope ===
        trend_slope = self.state.trend_slope.get(product, 0)
        
        # === Calculate trend-adjusted fair value ===
        # For upward trending product, fair value should be ahead of current price
        # Project fair value forward based on trend
        look_ahead = 10  # ticks
        trend_adjusted_fv = fair_value + (trend_slope * look_ahead)
        
        # Use a blend of EMA fair value and trend projection
        effective_fv = 0.7 * fair_value + 0.3 * trend_adjusted_fv

        # === Deviation from effective fair value ===
        deviation = (effective_fv - mid_price) / effective_fv if effective_fv > 0 else 0
        abs_deviation = abs(deviation)
        min_dev = config["min_deviation_pct"]

        # === Trend direction bias ===
        # Positive momentum = uptrend = prefer long positions
        is_uptrend = momentum > 0.0005
        is_downtrend = momentum < -0.0005
        
        # Adjust position limits based on trend
        effective_max_long = max_position
        effective_max_short = max_position
        
        if is_uptrend:
            # In uptrend: allow full long, restrict short
            effective_max_short = max_position // 2
        elif is_downtrend:
            # In downtrend: restrict long, allow full short
            effective_max_long = max_position // 2

        # === Inventory skew ===
        if max_position > 0:
            inventory_ratio = current_position / max_position
        else:
            inventory_ratio = 0

        # === Volatility adjustment ===
        vol_multiplier = 1.0 + (abs_deviation * 30)
        adjusted_spread = base_half_spread * vol_multiplier

        # === Skew calculation ===
        skew = inventory_ratio * INVENTORY_SKEW_FACTOR * adjusted_spread

        # === Calculate optimal bid/ask ===
        our_bid = int(effective_fv - adjusted_spread + skew)
        our_ask = int(effective_fv + adjusted_spread + skew)

        # Ensure minimum spread
        if our_ask - our_bid < 2:
            midpoint = (our_bid + our_ask) // 2
            our_bid = midpoint - 1
            our_ask = midpoint + 1

        # Don't cross the market
        if order_depth.buy_orders and order_depth.sell_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            
            our_bid = min(our_bid, best_ask - 1)
            our_ask = max(our_ask, best_bid + 1)

            # Aggressive orders when deviation is significant
            if abs_deviation >= min_dev:
                if deviation > 0 and is_uptrend:
                    # Price below FV + uptrend = strong buy signal
                    aggressive_bid = int(effective_fv - adjusted_spread * 0.3 + skew)
                    our_bid = max(our_bid, min(aggressive_bid, best_ask - 1))
                    # Increase order size on strong signals
                    order_size = int(order_size * 1.2)
                elif deviation < 0:
                    # Price above FV = sell
                    aggressive_ask = int(effective_fv + adjusted_spread * 0.3 + skew)
                    our_ask = min(our_ask, max(aggressive_ask, best_bid + 1))

        # === Place orders with trend-adjusted limits ===
        if current_position < effective_max_long:
            buy_qty = min(order_size, effective_max_long - current_position)
            if buy_qty > 0:
                orders.append(Order(product, our_bid, buy_qty))

        if current_position > -effective_max_short:
            sell_qty = min(order_size, effective_max_short + current_position)
            if sell_qty > 0:
                orders.append(Order(product, our_ask, -sell_qty))

        return orders
