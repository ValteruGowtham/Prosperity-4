"""
Prosperity 4 - Round 1 Trading Algorithm v2.0
Products: ASH_COATED_OSMIUM, INTARIAN_PEPPER_ROOT

v2.0 FIX based on performance analysis:
- ASH_COATED_OSMIUM: +1296 XIRECS ✅ Keep working strategy
- INTARIAN_PEPPER_ROOT: -1692 XIRECS ❌ Skip entirely (trend-fighting bug)

Root cause of v1.0 failure:
- Pepper strategy was SHORT-biased (mean-reversion)
- Price trended UP 100+ points continuously
- We accumulated -40 short position and held it
- Mark-to-market losses: -1692 XIRECS

Fix: Skip Pepper trading, focus only on profitable Osmium
Expected result: +1296 XIRECS instead of -395
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
# Product Configuration (v2.0 - Osmium only)
# ============================================================
PRODUCT_CONFIG = {
    "ASH_COATED_OSMIUM": {
        # PROVEN STRATEGY: Mean-reversion market making
        # v1.0 result: +1296.56 XIRECS ✅
        "fair_value_default": 10000,
        "target_half_spread": 4,       # Tight spread
        "order_size": 10,              # Large orders (stable product)
        "max_position": 40,            # Half of 80 limit
        "min_deviation_pct": 0.0003,   # Low threshold for frequent trades
        "ema_alpha": 0.05,             # Slow adaptation (very stable)
    },
    # INTARIAN_PEPPER_ROOT: DISABLED in v2.0
    # v1.0 result: -1692.00 XIRECS ❌
    # Reason: Trend-fighting bug (accumulated short position in uptrend)
    # Fix: Skip until proper trend-following strategy is implemented
}

# Global settings
INVENTORY_SKEW_FACTOR = 0.3
MOMENTUM_WINDOW = 10
MOMENTUM_THRESHOLD = 0.0002


# ============================================================
# State Management (serialized via traderData)
# ============================================================
class SerializableState:
    """All state that must persist across Lambda invocations."""

    def __init__(self):
        self.fair_value: Dict[str, float] = {}
        self.price_history: Dict[str, List[float]] = {}
        self.internal_position: Dict[str, int] = {}
        self.last_timestamp: int = 0
        self.initialized: bool = False

    def to_dict(self) -> dict:
        return {
            "fair_value": self.fair_value,
            "price_history": self.price_history,
            "internal_position": self.internal_position,
            "last_timestamp": self.last_timestamp,
            "initialized": self.initialized,
        }

    @staticmethod
    def from_dict(data: dict) -> "SerializableState":
        state = SerializableState()
        state.fair_value = data.get("fair_value", {})
        state.price_history = data.get("price_history", {})
        state.internal_position = data.get("internal_position", {})
        state.last_timestamp = data.get("last_timestamp", 0)
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
# Trader Class - Round 1 v2.0
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
            self.state.price_history = {}

        result: Dict[str, List[Order]] = {}

        # === Update positions from own_trades ===
        self._update_positions(state)

        # === Process ONLY ASH_COATED_OSMIUM (Pepper disabled) ===
        for product in state.order_depths:
            if product not in PRODUCT_CONFIG:
                # Skip all other products (including INTARIAN_PEPPER_ROOT)
                result[product] = []
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

            # Calculate momentum
            momentum = self._calculate_momentum(product, mid_price)

            # Generate orders (mean-reversion market making)
            orders = self._calculate_orders(
                product=product,
                config=config,
                order_depth=order_depth,
                fair_value=fair_value,
                mid_price=mid_price,
                current_position=current_position,
                momentum=momentum,
            )

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

    def _calculate_momentum(self, product: str, mid_price: int) -> float:
        """Calculate momentum from recent price history."""
        if product not in self.state.price_history:
            self.state.price_history[product] = []

        history = self.state.price_history[product]
        history.append(float(mid_price))

        # Keep last N prices
        if len(history) > MOMENTUM_WINDOW:
            self.state.price_history[product] = history[-MOMENTUM_WINDOW:]
            history = self.state.price_history[product]

        if len(history) < 3:
            return 0.0

        half = len(history) // 2
        first_avg = sum(history[:half]) / half
        second_avg = sum(history[half:]) / (len(history) - half)

        if first_avg == 0:
            return 0.0

        return (second_avg - first_avg) / first_avg

    def _calculate_orders(
        self,
        product: str,
        config: dict,
        order_depth: OrderDepth,
        fair_value: float,
        mid_price: int,
        current_position: int,
        momentum: float,
    ) -> List[Order]:
        """Calculate orders based on market conditions."""
        orders: List[Order] = []
        max_position = config["max_position"]
        order_size = config["order_size"]
        base_half_spread = config["target_half_spread"]

        # === Deviation check ===
        deviation = (fair_value - mid_price) / fair_value if fair_value > 0 else 0
        abs_deviation = abs(deviation)
        min_dev = config["min_deviation_pct"]

        # === Momentum filter ===
        should_trade = True
        if abs(momentum) > MOMENTUM_THRESHOLD:
            if deviation > 0 and momentum < -MOMENTUM_THRESHOLD * 2:
                should_trade = False
            elif deviation < 0 and momentum > MOMENTUM_THRESHOLD * 2:
                should_trade = False

        # === Inventory skew ===
        if max_position > 0:
            inventory_ratio = current_position / max_position
        else:
            inventory_ratio = 0

        # === Volatility adjustment ===
        vol_multiplier = 1.0 + (abs_deviation * 20)
        adjusted_spread = base_half_spread * vol_multiplier

        # === Skew calculation ===
        skew = inventory_ratio * INVENTORY_SKEW_FACTOR * adjusted_spread

        # === Calculate optimal bid/ask ===
        our_bid = int(fair_value - adjusted_spread + skew)
        our_ask = int(fair_value + adjusted_spread + skew)

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
            if abs_deviation >= min_dev and should_trade:
                if deviation > 0:
                    aggressive_bid = int(fair_value - adjusted_spread * 0.2 + skew)
                    our_bid = max(our_bid, min(aggressive_bid, best_ask - 1))
                elif deviation < 0:
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
