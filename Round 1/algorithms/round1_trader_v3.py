"""
Prosperity 4 - Round 1 Trading Algorithm v3.0
Products: ASH_COATED_OSMIUM, INTARIAN_PEPPER_ROOT

v3.0: Both products with optimized strategies

ASH_COATED_OSMIUM: Mean-reversion market making (PROVEN: +1296 XIRECS)
INTARIAN_PEPPER_ROOT: Conservative market making with LONG bias
  - Steady upward drift (+0.08% per 100 ticks)
  - Low volatility (std=29)
  - No mean reversion (50.5%)
  - No momentum (15% accuracy)
  - Strategy: Market make with LONG bias, tight limits (±15)
"""

import json
from typing import Dict, List, Optional, Tuple


# ============================================================
# Data Model Classes
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
# Product Configuration (v3.0 - Both products)
# ============================================================
PRODUCT_CONFIG = {
    "ASH_COATED_OSMIUM": {
        # PROVEN: Mean-reversion market making
        # v1.0/v2.0 result: +1296.56 XIRECS ✅
        "fair_value_default": 10000,
        "target_half_spread": 4,
        "order_size": 10,
        "max_position": 40,
        "min_deviation_pct": 0.0003,
        "ema_alpha": 0.05,
        "strategy": "mean_reversion",
    },
    "INTARIAN_PEPPER_ROOT": {
        # NEW v3.0: Conservative market making with LONG bias
        # Analysis: Steady upward drift (+0.08% per 100 ticks)
        # Low volatility (std=29), no mean reversion, no momentum
        "fair_value_default": 12000,
        "target_half_spread": 7,       # Wider spread (avg spread=13.71)
        "order_size": 5,               # Smaller orders (conservative)
        "max_position": 15,            # Tight limit (avoid v1.0 disaster)
        "min_deviation_pct": 0.0005,   # Moderate threshold
        "ema_alpha": 0.1,              # Moderate adaptation
        "strategy": "conservative_mm", # Conservative market making
        "long_bias": True,             # Bias toward LONG (upward drift)
    },
}

# Global settings
INVENTORY_SKEW_FACTOR = 0.3
MOMENTUM_WINDOW = 10


# ============================================================
# State Management
# ============================================================
class SerializableState:
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
# Trader Class - Round 1 v3.0
# ============================================================
class Trader:
    def __init__(self):
        self.state = SerializableState()
        self._initialized = False

    def bid(self):
        return 15

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        """Main trading method."""

        # Restore state
        if not self._initialized:
            self.state = SerializableState.deserialize(state.traderData)
            self._initialized = True

        if state.timestamp < self.state.last_timestamp:
            self.state.price_history = {}

        result: Dict[str, List[Order]] = {}
        self._update_positions(state)

        for product in state.order_depths:
            if product not in PRODUCT_CONFIG:
                result[product] = []
                continue

            config = PRODUCT_CONFIG[product]
            order_depth: OrderDepth = state.order_depths[product]
            current_position = state.position.get(
                product, self.state.internal_position.get(product, 0))

            mid_price = self._get_mid_price(order_depth)
            if mid_price is None:
                result[product] = []
                continue

            fair_value = self._update_fair_value(product, mid_price, config)
            momentum = self._calculate_momentum(product, mid_price)

            if config["strategy"] == "mean_reversion":
                orders = self._mean_reversion_orders(
                    product, config, order_depth, fair_value,
                    mid_price, current_position, momentum)
            elif config["strategy"] == "conservative_mm":
                orders = self._conservative_market_making(
                    product, config, order_depth, fair_value,
                    mid_price, current_position, momentum)
            else:
                orders = []

            result[product] = orders

        self.state.last_timestamp = state.timestamp
        trader_data = self.state.serialize()
        return result, 0, trader_data

    def _update_positions(self, state: TradingState):
        for product, trades in state.own_trades.items():
            if product not in self.state.internal_position:
                self.state.internal_position[product] = 0
            for trade in trades:
                if trade.buyer == "SUBMISSION":
                    self.state.internal_position[product] += trade.quantity
                elif trade.seller == "SUBMISSION":
                    self.state.internal_position[product] -= trade.quantity

    def _get_mid_price(self, order_depth: OrderDepth) -> Optional[int]:
        if order_depth.buy_orders and order_depth.sell_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            return (best_bid + best_ask) // 2
        return None

    def _update_fair_value(self, product: str, mid_price: int, config: dict) -> float:
        alpha = config["ema_alpha"]
        if product not in self.state.fair_value:
            self.state.fair_value[product] = float(mid_price)
            return self.state.fair_value[product]

        old_fv = self.state.fair_value[product]
        new_fv = alpha * mid_price + (1 - alpha) * old_fv
        self.state.fair_value[product] = new_fv
        return new_fv

    def _calculate_momentum(self, product: str, mid_price: int) -> float:
        if product not in self.state.price_history:
            self.state.price_history[product] = []

        history = self.state.price_history[product]
        history.append(float(mid_price))

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

    def _mean_reversion_orders(self, product, config, order_depth, fair_value,
                                mid_price, current_position, momentum):
        """ASH_COATED_OSMIUM: Mean-reversion market making."""
        orders = []
        max_position = config["max_position"]
        order_size = config["order_size"]
        base_half_spread = config["target_half_spread"]

        deviation = (fair_value - mid_price) / fair_value if fair_value > 0 else 0
        abs_deviation = abs(deviation)

        inventory_ratio = current_position / max_position if max_position > 0 else 0
        vol_multiplier = 1.0 + (abs_deviation * 20)
        adjusted_spread = base_half_spread * vol_multiplier
        skew = inventory_ratio * INVENTORY_SKEW_FACTOR * adjusted_spread

        our_bid = int(fair_value - adjusted_spread + skew)
        our_ask = int(fair_value + adjusted_spread + skew)

        if our_ask - our_bid < 2:
            midpoint = (our_bid + our_ask) // 2
            our_bid = midpoint - 1
            our_ask = midpoint + 1

        if order_depth.buy_orders and order_depth.sell_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            our_bid = min(our_bid, best_ask - 1)
            our_ask = max(our_ask, best_bid + 1)

        if current_position < max_position:
            buy_qty = min(order_size, max_position - current_position)
            if buy_qty > 0:
                orders.append(Order(product, our_bid, buy_qty))

        if current_position > -max_position:
            sell_qty = min(order_size, max_position + current_position)
            if sell_qty > 0:
                orders.append(Order(product, our_ask, -sell_qty))

        return orders

    def _conservative_market_making(self, product, config, order_depth, fair_value,
                                     mid_price, current_position, momentum):
        """INTARIAN_PEPPER_ROOT: Conservative MM with LONG bias."""
        orders = []
        max_position = config["max_position"]
        order_size = config["order_size"]
        base_half_spread = config["target_half_spread"]
        long_bias = config.get("long_bias", False)

        deviation = (fair_value - mid_price) / fair_value if fair_value > 0 else 0
        abs_deviation = abs(deviation)

        # LONG bias: adjust effective position limits
        if long_bias:
            # Allow more long, restrict short
            max_long = max_position
            max_short = max_position // 2  # Only half the short limit
        else:
            max_long = max_position
            max_short = max_position

        inventory_ratio = current_position / max_position if max_position > 0 else 0
        vol_multiplier = 1.0 + (abs_deviation * 30)  # More conservative
        adjusted_spread = base_half_spread * vol_multiplier
        skew = inventory_ratio * INVENTORY_SKEW_FACTOR * adjusted_spread

        # For LONG bias, skew bids higher (more aggressive buying)
        if long_bias and current_position < 0:
            # If short, be more aggressive on buys to cover
            our_bid = int(fair_value - adjusted_spread * 0.7 + skew)
            our_ask = int(fair_value + adjusted_spread * 1.3 + skew)
        else:
            our_bid = int(fair_value - adjusted_spread + skew)
            our_ask = int(fair_value + adjusted_spread + skew)

        if our_ask - our_bid < 2:
            midpoint = (our_bid + our_ask) // 2
            our_bid = midpoint - 1
            our_ask = midpoint + 1

        if order_depth.buy_orders and order_depth.sell_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            our_bid = min(our_bid, best_ask - 1)
            our_ask = max(our_ask, best_bid + 1)

        # Place orders with bias-adjusted limits
        if current_position < max_long:
            buy_qty = min(order_size, max_long - current_position)
            if buy_qty > 0:
                orders.append(Order(product, our_bid, buy_qty))

        if current_position > -max_short:
            sell_qty = min(order_size, max_short + current_position)
            if sell_qty > 0:
                orders.append(Order(product, our_ask, -sell_qty))

        return orders
