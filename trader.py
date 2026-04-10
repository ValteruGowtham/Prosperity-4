"""
Prosperity 4 - Algorithmic Trading Bot v11.0
Strategy: Conservative Enhancement (Surgical Fix on v3.0 Baseline)

v11.0: TWO SURGICAL IMPROVEMENTS on v3.0 (+1195 PNL)
1. Opportunistic fills: When flat + strong signal + momentum agreement, add small orders at best bid/ask
2. Position-aware unwinding: 3 zones (normal, caution, danger) to prevent getting stuck at limits

All v3.0 logic preserved:
- Full state persistence via traderData
- EMA-based fair value
- State-aware momentum filtering
- Conservative base parameters (TOMATOES: size 5, spread 4; EMERALDS: size 8, spread 3)
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
# Product Configuration (v3.0 baseline — KEEP THESE)
# ============================================================
PRODUCT_CONFIG = {
    "EMERALDS": {
        "fair_value_default": 10000,
        "target_half_spread": 3,
        "order_size": 8,
        "max_position": 20,
        "min_deviation_pct": 0.0005,
        "ema_alpha": 0.1,
    },
    "TOMATOES": {
        "fair_value_default": 5000,
        "target_half_spread": 4,
        "order_size": 5,
        "max_position": 15,
        "min_deviation_pct": 0.001,
        "ema_alpha": 0.15,
    },
}

# Global settings (v3.0 baseline)
INVENTORY_SKEW_FACTOR = 0.3
MOMENTUM_WINDOW = 5
MOMENTUM_THRESHOLD = 0.0005


# ============================================================
# State Management (serialized via traderData)
# ============================================================
class SerializableState:
    def __init__(self):
        self.fair_value: Dict[str, float] = {}
        self.price_history: Dict[str, List[int]] = {}
        self.internal_position: Dict[str, int] = {}
        self.last_timestamp: int = 0

    def to_dict(self) -> dict:
        return {
            "fair_value": self.fair_value,
            "price_history": self.price_history,
            "internal_position": self.internal_position,
            "last_timestamp": self.last_timestamp,
        }

    @staticmethod
    def from_dict(data: dict) -> "SerializableState":
        state = SerializableState()
        state.fair_value = data.get("fair_value", {})
        state.price_history = data.get("price_history", {})
        state.internal_position = data.get("internal_position", {})
        state.last_timestamp = data.get("last_timestamp", 0)
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
# Trader Class (v11.0)
# ============================================================
class Trader:
    def __init__(self):
        self.state = SerializableState()
        self._initialized = False

    def bid(self):
        return 15

    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        """Main trading method."""
        # Restore state from traderData
        if not self._initialized:
            self.state = SerializableState.deserialize(state.traderData)
            self._initialized = True

        # Detect reset
        if state.timestamp < self.state.last_timestamp:
            self.state.price_history = {}

        result: Dict[str, List[Order]] = {}

        # Update positions from own_trades
        self._update_positions(state)

        # Process each product
        for product in state.order_depths:
            if product not in PRODUCT_CONFIG:
                continue

            config = PRODUCT_CONFIG[product]
            order_depth: OrderDepth = state.order_depths[product]

            # Get current position
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

            # Generate orders
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

        # Save state
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
        if order_depth.buy_orders and order_depth.sell_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            return (best_bid + best_ask) // 2
        return None

    def _update_fair_value(self, product: str, mid_price: int, config: dict) -> float:
        """EMA-based fair value."""
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

    # ============================================================
    # v11.0 Surgical Fix #2: Position-Aware Order Calculation
    # 3 zones: Normal (0-60%), Caution (60-80%), Danger (80%+)
    # ============================================================
    def _calculate_position_aware_orders(
        self,
        product: str,
        config: dict,
        order_depth: OrderDepth,
        fair_value: float,
        current_position: int,
        max_position: int,
        adjusted_spread: float,
        skew: float,
    ) -> List[Order]:
        """
        Zone 1: Normal (0-60%) — use passive orders normally
        Zone 2: Caution (60-80%) — tighten spread by 20% for unwinding side
        Zone 3: Danger (80%+) — aggressive unwinding at best bid/ask
        """
        position_ratio = abs(current_position) / max_position if max_position > 0 else 0

        # Zone 3: Danger — must unwind aggressively
        if position_ratio >= 0.8:
            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())

            if current_position > max_position * 0.8:
                # Too long — MUST sell at best ask
                sell_qty = min(config["order_size"], current_position + max_position)
                return [Order(product, best_ask, -sell_qty)]
            else:
                # Too short — MUST buy at best bid
                buy_qty = min(config["order_size"], max_position - current_position)
                return [Order(product, best_bid, buy_qty)]

        # Zone 2: Caution — tighten spread for unwinding side
        if position_ratio >= 0.6:
            base_spread = config["target_half_spread"]
            tight_spread = base_spread * 0.8  # Tighten by 20%

            # Calculate orders with tightened spread
            our_bid = int(fair_value - tight_spread + skew)
            our_ask = int(fair_value + tight_spread + skew)

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

            orders = []
            if current_position < max_position:
                buy_qty = min(config["order_size"], max_position - current_position)
                if buy_qty > 0:
                    orders.append(Order(product, our_bid, buy_qty))
            if current_position > -max_position:
                sell_qty = min(config["order_size"], max_position + current_position)
                if sell_qty > 0:
                    orders.append(Order(product, our_ask, -sell_qty))
            return orders

        # Zone 1: Normal — use passed-in adjusted spread
        return None  # Signal to use normal calculation

    # ============================================================
    # v11.0 Surgical Fix #1: Opportunistic Fills When Flat
    # Only when flat + strong signal + momentum agreement
    # ============================================================
    def _add_opportunistic_fills(
        self,
        product: str,
        orders: List[Order],
        current_position: int,
        deviation: float,
        momentum: float,
        config: dict,
        order_depth: OrderDepth,
    ) -> List[Order]:
        """Add small opportunistic orders only when all guards pass."""

        # Guard 1: Must be flat enough (abs position <= 5)
        if abs(current_position) > 5:
            return orders

        # Guard 2: Signal must be strong enough (2x normal threshold)
        if abs(deviation) < config["min_deviation_pct"] * 2.0:
            return orders

        # Guard 3: Momentum must agree with deviation
        momentum_agrees = (
            (deviation > 0 and momentum >= 0) or  # Both bullish
            (deviation < 0 and momentum <= 0)     # Both bearish
        )
        if not momentum_agrees:
            return orders

        # All guards passed — add ONE small opportunistic order
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        small_size = config["order_size"] // 2  # Half normal size

        if deviation > 0:
            # Price below fair value → join best bid (don't cross spread!)
            orders.append(Order(product, best_bid, small_size))
        else:
            # Price above fair value → join best ask (don't cross spread!)
            orders.append(Order(product, best_ask, -small_size))

        return orders

    # ============================================================
    # Main Order Calculation (v3.0 baseline + v11.0 surgical fixes)
    # ============================================================
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
        """v11.0: v3.0 baseline with two surgical improvements."""
        orders: List[Order] = []
        max_position = config["max_position"]
        base_half_spread = config["target_half_spread"]

        # === Deviation ===
        deviation = (fair_value - mid_price) / fair_value if fair_value > 0 else 0
        abs_deviation = abs(deviation)
        min_dev = config["min_deviation_pct"]

        # === Momentum filter ===
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
        vol_multiplier = 1.0 + (abs_deviation * 50)
        adjusted_spread = base_half_spread * vol_multiplier

        # === Skew calculation ===
        skew = inventory_ratio * INVENTORY_SKEW_FACTOR * adjusted_spread

        # === v11.0 Fix #2: Position-aware orders (3 zones) ===
        position_orders = self._calculate_position_aware_orders(
            product, config, order_depth, fair_value,
            current_position, max_position, adjusted_spread, skew
        )

        if position_orders is not None:
            # Zone 2 or 3 handled — return these orders + opportunistic fills
            orders = position_orders
        else:
            # Zone 1: Normal — calculate passive orders normally
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

                # Aggressive passive orders when deviation is significant
                if abs_deviation >= min_dev and should_trade_aggressive:
                    if deviation > 0:
                        aggressive_bid = int(fair_value - adjusted_spread * 0.3 + skew)
                        our_bid = max(our_bid, min(aggressive_bid, best_ask - 1))
                    elif deviation < 0:
                        aggressive_ask = int(fair_value + adjusted_spread * 0.3 + skew)
                        our_ask = min(our_ask, max(aggressive_ask, best_bid + 1))

            # Place passive orders
            if current_position < max_position:
                buy_qty = min(config["order_size"], max_position - current_position)
                if buy_qty > 0:
                    orders.append(Order(product, our_bid, buy_qty))

            if current_position > -max_position:
                sell_qty = min(config["order_size"], max_position + current_position)
                if sell_qty > 0:
                    orders.append(Order(product, our_ask, -sell_qty))

        # === v11.0 Fix #1: Opportunistic fills when flat + strong signal ===
        if order_depth.buy_orders and order_depth.sell_orders:
            orders = self._add_opportunistic_fills(
                product, orders, current_position, deviation,
                momentum, config, order_depth
            )

        return orders
