"""
Prosperity 4 - Algorithmic Trading Bot v4.0
Strategy: Aggressive Mean-Reversion Market Maker

v4.0 Improvements over v3.0:
- EMERALDS optimized for maximum turnover (tighter spread, larger orders)
- Position recycling: actively seek to trade even when flat
- Adaptive spread: tighten when no fills, widen when getting filled
- Dual-mode trading: passive + opportunistic aggressive orders
- Better fill rate tracking via traderData
"""

import json
from typing import Dict, List, Optional, Tuple, Any
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
# Product Configuration (v4.0 optimized)
# ============================================================
PRODUCT_CONFIG = {
    "EMERALDS": {
        "fair_value_default": 10000,
        "target_half_spread": 2,       # v4.0: was 3 → 2 (ultra-tight for max fills)
        "order_size": 12,              # v4.0: was 8 → 12 (bigger for faster turnover)
        "max_position": 20,
        "min_deviation_pct": 0.0003,   # v4.0: was 0.0005 → 0.0003 (more aggressive)
        "ema_alpha": 0.1,
        "volatility_lookback": 10,
        # v4.0: EMERALDS-specific aggressive mode
        "aggressive_half_spread": 1,   # When flat, use even tighter spread
        "aggressive_order_size": 15,   # When flat, place bigger orders
    },
    "TOMATOES": {
        "fair_value_default": 5000,
        "target_half_spread": 3,       # v4.0: was 4 → 3 (slightly tighter)
        "order_size": 6,               # v4.0: was 5 → 6 (slightly bigger)
        "max_position": 15,
        "min_deviation_pct": 0.0008,   # v4.0: was 0.001 → 0.0008 (more aggressive)
        "ema_alpha": 0.15,
        "volatility_lookback": 10,
        "aggressive_half_spread": 2,
        "aggressive_order_size": 8,
    },
}

# Global settings
INVENTORY_SKEW_FACTOR = 0.25           # v4.0: was 0.3 → 0.25 (less skew = more fills)
MOMENTUM_WINDOW = 5
MOMENTUM_THRESHOLD = 0.0008            # v4.0: was 0.0005 → 0.0008 (even more relaxed)
FILL_TRACK_WINDOW = 20                 # Track fills over last 20 iterations


# ============================================================
# State Management (serialized via traderData)
# ============================================================
class SerializableState:
    """All state that must persist across Lambda invocations."""

    def __init__(self):
        self.fair_value: Dict[str, float] = {}
        self.price_history: Dict[str, List[int]] = {}
        self.internal_position: Dict[str, int] = {}
        self.last_timestamp: int = 0
        # v4.0: Fill tracking for adaptive spread
        self.recent_fills: Dict[str, List[bool]] = {}  # True if filled in last N iterations
        self.iteration_count: Dict[str, int] = {}  # Total iterations per product
        self.fills_in_window: Dict[str, int] = {}  # Fills in recent window

    def to_dict(self) -> dict:
        return {
            "fair_value": self.fair_value,
            "price_history": self.price_history,
            "internal_position": self.internal_position,
            "last_timestamp": self.last_timestamp,
            "recent_fills": self.recent_fills,
            "iteration_count": self.iteration_count,
            "fills_in_window": self.fills_in_window,
        }

    @staticmethod
    def from_dict(data: dict) -> "SerializableState":
        state = SerializableState()
        state.fair_value = data.get("fair_value", {})
        state.price_history = data.get("price_history", {})
        state.internal_position = data.get("internal_position", {})
        state.last_timestamp = data.get("last_timestamp", 0)
        state.recent_fills = data.get("recent_fills", {})
        state.iteration_count = data.get("iteration_count", {})
        state.fills_in_window = data.get("fills_in_window", {})
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
# Trader Class (v4.0)
# ============================================================
class Trader:
    def __init__(self):
        self.state = SerializableState()
        self._initialized = False

    def bid(self):
        return 15

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        """Main trading method called by the platform each iteration."""

        # === Restore state from traderData ===
        if not self._initialized:
            self.state = SerializableState.deserialize(state.traderData)
            self._initialized = True

        # Detect reset
        if state.timestamp < self.state.last_timestamp:
            self.state.price_history = {}

        result: Dict[str, List[Order]] = {}

        # === Update positions from own_trades ===
        had_fills = self._update_positions(state)

        # === Process each product ===
        for product in state.order_depths:
            if product not in PRODUCT_CONFIG:
                continue

            config = PRODUCT_CONFIG[product]
            order_depth: OrderDepth = state.order_depths[product]

            # Get position
            current_position = state.position.get(product, self.state.internal_position.get(product, 0))

            # Calculate mid price
            mid_price = self._get_mid_price(order_depth)
            if mid_price is None:
                result[product] = []
                continue

            # Update fair value using EMA
            fair_value = self._update_fair_value(product, mid_price, config)

            # Calculate momentum
            momentum = self._calculate_momentum(product, mid_price)

            # Track fills for adaptive spread
            self._track_fills(product, had_fills.get(product, False))

            # Generate orders with adaptive spread
            orders = self._calculate_orders_v4(
                product=product,
                config=config,
                order_depth=order_depth,
                fair_value=fair_value,
                mid_price=mid_price,
                current_position=current_position,
                momentum=momentum,
            )

            result[product] = orders

        # === Save state ===
        self.state.last_timestamp = state.timestamp
        trader_data = self.state.serialize()
        conversions = 0

        return result, conversions, trader_data

    def _update_positions(self, state: TradingState) -> Dict[str, bool]:
        """Update internal position tracker from own_trades. Returns dict of which products had fills."""
        had_fills: Dict[str, bool] = {}
        for product, trades in state.own_trades.items():
            if product not in self.state.internal_position:
                self.state.internal_position[product] = 0
                had_fills[product] = False

            if trades:
                had_fills[product] = True
                for trade in trades:
                    if trade.buyer == "SUBMISSION":
                        self.state.internal_position[product] += trade.quantity
                    elif trade.seller == "SUBMISSION":
                        self.state.internal_position[product] -= trade.quantity
            else:
                had_fills[product] = False

        return had_fills

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
        history.append(mid_price)
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

    def _track_fills(self, product: str, had_fill: bool):
        """Track recent fills for adaptive spread adjustment."""
        if product not in self.state.recent_fills:
            self.state.recent_fills[product] = []
            self.state.iteration_count[product] = 0
            self.state.fills_in_window[product] = 0

        history = self.state.recent_fills[product]
        history.append(had_fill)
        self.state.iteration_count[product] = self.state.iteration_count.get(product, 0) + 1

        # Keep only last N
        if len(history) > FILL_TRACK_WINDOW:
            old_fill = history.pop(0)
            if old_fill:
                self.state.fills_in_window[product] = max(0, self.state.fills_in_window[product] - 1)

        if had_fill:
            self.state.fills_in_window[product] = self.state.fills_in_window.get(product, 0) + 1

    def _get_fill_rate(self, product: str) -> float:
        """Get recent fill rate (0.0 to 1.0)."""
        count = self.state.iteration_count.get(product, 0)
        if count == 0:
            return 0.0
        fills = self.state.fills_in_window.get(product, 0)
        window_size = min(FILL_TRACK_WINDOW, count)
        return fills / window_size if window_size > 0 else 0.0

    def _calculate_orders_v4(
        self,
        product: str,
        config: dict,
        order_depth: OrderDepth,
        fair_value: float,
        mid_price: int,
        current_position: int,
        momentum: float,
    ) -> List[Order]:
        """v4.0: Calculate orders with adaptive spread and position recycling."""
        orders: List[Order] = []
        max_position = config["max_position"]
        base_half_spread = config["target_half_spread"]
        order_size = config["order_size"]

        # === v4.0: Adaptive spread based on fill rate ===
        fill_rate = self._get_fill_rate(product)

        if fill_rate < 0.1 and abs(current_position) < max_position * 0.5:
            # Low fill rate + not at position limit → get aggressive
            half_spread = config.get("aggressive_half_spread", base_half_spread)
            order_size = config.get("aggressive_order_size", order_size)
        elif fill_rate > 0.6:
            # High fill rate → can widen slightly to earn more spread
            half_spread = base_half_spread + 1
        else:
            half_spread = base_half_spread

        # === Deviation and momentum ===
        deviation = (fair_value - mid_price) / fair_value if fair_value > 0 else 0
        abs_deviation = abs(deviation)
        min_dev = config["min_deviation_pct"]

        should_trade_aggressive = True
        if abs(momentum) > MOMENTUM_THRESHOLD:
            if deviation > 0 and momentum < -MOMENTUM_THRESHOLD:
                should_trade_aggressive = False
            elif deviation < 0 and momentum > MOMENTUM_THRESHOLD:
                should_trade_aggressive = False

        # === Inventory skew ===
        if max_position > 0:
            inventory_ratio = current_position / max_position
        else:
            inventory_ratio = 0

        # === Volatility adjustment ===
        vol_multiplier = 1.0 + (abs_deviation * 30)  # v4.0: reduced from 50
        adjusted_spread = half_spread * vol_multiplier

        # === Skew ===
        skew = inventory_ratio * INVENTORY_SKEW_FACTOR * adjusted_spread

        # === Passive orders ===
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

            # === v4.0: Aggressive orders when conditions are right ===
            if abs_deviation >= min_dev and should_trade_aggressive:
                if deviation > 0:
                    aggressive_bid = int(fair_value - adjusted_spread * 0.2 + skew)
                    our_bid = max(our_bid, min(aggressive_bid, best_ask - 1))
                elif deviation < 0:
                    aggressive_ask = int(fair_value + adjusted_spread * 0.2 + skew)
                    our_ask = min(our_ask, max(aggressive_ask, best_bid + 1))

            # === v4.0: Position recycling — when flat, be aggressive on ONE side ===
            if abs(current_position) < 3 and fill_rate < 0.2:
                # We're nearly flat and not getting fills
                if deviation > 0.0001:
                    # Price below fair value → aggressive BUY
                    our_bid = max(our_bid, best_ask - 1)
                elif deviation < -0.0001:
                    # Price above fair value → aggressive SELL
                    our_ask = min(our_ask, best_bid + 1)
                else:
                    # Price at fair value → slightly aggressive on both sides
                    our_bid = max(our_bid, best_bid + 1)
                    our_ask = min(our_ask, best_ask - 1)

        # === Safety: ensure bid < ask (no crossed orders) ===
        if our_bid >= our_ask:
            midpoint = (our_bid + our_ask) // 2
            our_bid = midpoint - 1
            our_ask = midpoint + 1

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
