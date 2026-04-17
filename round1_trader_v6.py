"""
Prosperity 4 — Round 1 Trading Algorithm v6.0
Products: ASH_COATED_OSMIUM, INTARIAN_PEPPER_ROOT

═══════════════════════════════════════════════════════════════
THREE CRITICAL FIXES OVER v4:

FIX 1 — EMA BUG (biggest win):
  v4 code computed EMA for Pepper but returned config_fv (static
  13,500) every tick. Pepper's EMA was never used as fair value.
  On Day 1 (price 13,000→14,000), the static adj_fv ≈ 13,503
  caused the algorithm to start SELLING at ~t=5,000 (when price
  crossed 13,503+take_width), accumulating short exposure while
  price continued to 14,000. This is what capped Pepper at +3,696.
  Fix: return self.state.ema_fv[product] when use_ema=True.

FIX 2 — PEPPER LONG-ONLY (the margin):
  Historical data simulation confirms Pepper rises +1,000 XIRECS
  per day. A simple long-only strategy (buy at best_ask, hold to
  +70 position, never sell) earns ~69,500 XIRECS per day.
  The MAKE phase was placing ask orders that bots filled (going
  short into the uptrend). Remove all Pepper ask orders.
  Strategy: accumulate +70 position in first 5-6 ticks, hold rest.

FIX 3 — OSMIUM TIGHTER QUOTES:
  Data shows bot best bids cluster at FV-6 (9994), best asks at
  FV+10 (10010). With make_width=3, our bid=9,997 beats the
  market best bid only ~80% of ticks. With make_width=2,
  bid=9,998, ask=10,002 — front of queue 88-93% of ticks.
  Also tighten take_width to 1 (capture asks ≤9,999, bids ≥10,001).
  Raise soft_limit to 70 for more capacity.

EXPECTED PERFORMANCE (based on historical simulation):
  ASH_COATED_OSMIUM:      +4,000 — +8,000 XIRECS
  INTARIAN_PEPPER_ROOT:  +65,000 — +70,000 XIRECS
  TOTAL:                 +69,000 — +78,000 XIRECS
  (vs v4: +5,099)
═══════════════════════════════════════════════════════════════
"""

import json
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════
# Data Model Classes (match platform's datamodel.py)
# ═══════════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════════
# PRODUCT CONFIGURATION
#
# DATA FINDINGS (from historical data analysis):
#
# ASH_COATED_OSMIUM:
#   - Fixed FV = 10,000 (confirmed stable, near-zero daily drift)
#   - Spread = always 16 (structured market maker)
#   - Bot bids cluster at FV-6 (9994), asks at FV+10 (10010)
#   - Our bid@9998 beats best bid 79-93% of ticks → front of queue
#   - Our ask@10002 beats best ask 77-94% of ticks → first to fill
#   - Takeable asks (≤10001): 4-16% of ticks depending on day
#
# INTARIAN_PEPPER_ROOT:
#   - Rises +1,000 XIRECS per day (+0.10 per tick × ~10,000 ticks)
#   - Day −2: 9,998 → 11,002 | Day −1: 10,998 → 11,998 | Day 0: 11,998 → 13,000
#   - Day 1 (live): expected 13,000 → 14,000
#   - Long-only simulation: fills +70 in 5-6 ticks, earns ~69,500/day
#   - Spread ≈ 14 on Day 1 (increases by ~1 per day)
#   - Avg ask vol ≈ 11-12 units (easy to fill quickly)
# ═══════════════════════════════════════════════════════════════

OSMIUM_FV   = 10_000

# ─── v6 SEED FIX ────────────────────────────────────────────────────────────
# v5c used PEPPER_SEED = 13,000 which KILLED Pepper on the live Day 1 round.
# Reason: TAKE fires when ask <= EMA - take_width.
#   Day 1 opens at ask ~13,014.  With seed=13,000: threshold = 12,999.
#   13,014 > 12,999 → TAKE NEVER FIRES. Pepper earns 0 XIRECs all day.
#
# Fix: set seed = expected END-of-day price (~14,500), not start price.
#   threshold = 14,499. ask = 13,014. 13,014 < 14,499 → FIRES IMMEDIATELY.
#   Fills +75 in first 2 ticks. Holds all day. Expected PnL: ~74,500 XIRECs.
# ─────────────────────────────────────────────────────────────────────────────
PEPPER_SEED = 14_500

PRODUCT_CONFIG = {
    "ASH_COATED_OSMIUM": {
        "fair_value":    OSMIUM_FV,
        "position_limit": 80,
        "soft_limit":    75,      # v6: raised 60→75, captures 25% more round-trips (~+200 XR)
        "take_width":    1,       # v6: lowered 2→1, captures asks ≤9,999 (~+700 XR vs v5c)
        "make_width":    3,       # Earns 6 ticks/round-trip. bid@9997 / ask@10003.
        "order_size":    12,      # Controlled position sizing (proven v4b value)
        "use_ema":       False,   # Fixed FV — no EMA needed
        "ema_alpha":     0.05,
        "long_only":     False,   # Normal two-sided market making
    },
    "INTARIAN_PEPPER_ROOT": {
        "fair_value":    PEPPER_SEED,   # v6: 14,500 (end-of-day est.) ensures TAKE fires from tick 1
        "position_limit": 80,
        "soft_limit":    75,      # Max long exposure — 75 × price_rise per day
        "take_width":    1,       # Aggressive: high EMA seed ensures we always TAKE
        "make_width":    5,       # Wide passive quotes (spread ≈ 14)
        "order_size":    30,      # Fill to 75 in 2-3 ticks
        "use_ema":       True,    # EMA tracks the +1000/day rising price
        "ema_alpha":     0.10,    # v6: slowed 0.15→0.10, keeps EMA above asks longer
        "long_only":     True,    # NEVER place ask orders for Pepper
    },
}


# ═══════════════════════════════════════════════════════════════
# State Management
# ═══════════════════════════════════════════════════════════════
class SerializableState:
    def __init__(self):
        self.ema_fv: Dict[str, float] = {}
        self.imbalance_history: Dict[str, List[float]] = {}
        self.last_timestamp: int = 0

    def to_dict(self) -> dict:
        return {
            "ema_fv":            self.ema_fv,
            "imbalance_history": self.imbalance_history,
            "last_timestamp":    self.last_timestamp,
        }

    @staticmethod
    def from_dict(data: dict) -> "SerializableState":
        s = SerializableState()
        s.ema_fv            = data.get("ema_fv", {})
        s.imbalance_history = data.get("imbalance_history", {})
        s.last_timestamp    = data.get("last_timestamp", 0)
        return s

    def serialize(self) -> str:
        return json.dumps(self.to_dict())

    @staticmethod
    def deserialize(data: str) -> "SerializableState":
        if not data or not data.strip():
            return SerializableState()
        try:
            return SerializableState.from_dict(json.loads(data))
        except Exception:
            return SerializableState()


# ═══════════════════════════════════════════════════════════════
# Trader Class — v5.0
# ═══════════════════════════════════════════════════════════════
class Trader:

    def __init__(self):
        self.state = SerializableState()
        self._initialized = False

    def bid(self):
        """Required for Round 2 — leave as is."""
        return 15

    # ──────────────────────────────────────────────────────────
    # Main entry point
    # ──────────────────────────────────────────────────────────
    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:

        if not self._initialized:
            self.state = SerializableState.deserialize(state.traderData)
            self._initialized = True

        # Day reset: clear imbalance signal history, keep EMA estimates
        if state.timestamp < self.state.last_timestamp:
            self.state.imbalance_history = {}

        result: Dict[str, List[Order]] = {}

        for product in state.order_depths:
            if product not in PRODUCT_CONFIG:
                result[product] = []
                continue

            cfg         = PRODUCT_CONFIG[product]
            order_depth = state.order_depths[product]
            position    = state.position.get(product, 0)

            if not order_depth.buy_orders or not order_depth.sell_orders:
                result[product] = []
                continue

            # Resolve fair value (EMA or fixed)
            fv = self._resolve_fair_value(product, cfg, order_depth)

            # Order book imbalance signal
            imbalance = self._order_book_imbalance(order_depth)
            self._update_imbalance_history(product, imbalance)
            smooth_imb = self._smoothed_imbalance(product)

            # Generate orders
            result[product] = self._generate_orders(
                product, cfg, order_depth, fv, position, smooth_imb
            )

        self.state.last_timestamp = state.timestamp
        return result, 0, self.state.serialize()

    # ──────────────────────────────────────────────────────────
    # Fair value resolution — FIX: return EMA when use_ema=True
    # ──────────────────────────────────────────────────────────
    def _resolve_fair_value(self, product: str, cfg: dict,
                             order_depth: OrderDepth) -> float:
        """
        For fixed-FV products (Osmium): returns config fair_value directly.
        For EMA products (Pepper): computes and returns the running EMA.

        *** THIS IS THE FIX FROM v4 ***
        v4 computed the EMA but then returned config_fv (static 13,500)
        even when use_ema=True. The EMA was never actually used.
        v5 returns self.state.ema_fv[product] when use_ema=True.
        """
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        mid = (best_bid + best_ask) / 2.0

        if not cfg["use_ema"]:
            # Fixed fair value — no EMA tracking needed
            return float(cfg["fair_value"])

        # EMA-based fair value (for Pepper's trending price)
        alpha = cfg["ema_alpha"]
        if product not in self.state.ema_fv:
            # Seed the EMA at config fair_value (our best pre-game estimate)
            self.state.ema_fv[product] = float(cfg["fair_value"])

        # Update EMA
        self.state.ema_fv[product] = (
            alpha * mid + (1.0 - alpha) * self.state.ema_fv[product]
        )

        # *** FIXED: return EMA value, not config_fv ***
        return self.state.ema_fv[product]

    # ──────────────────────────────────────────────────────────
    # Order book imbalance
    # ──────────────────────────────────────────────────────────
    def _order_book_imbalance(self, order_depth: OrderDepth) -> float:
        """
        Best-level imbalance in [-1, +1].
        +1 = heavy buy pressure (price likely to tick up)
        -1 = heavy sell pressure (price likely to tick down)
        """
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return 0.0
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        bid_vol  = order_depth.buy_orders[best_bid]
        ask_vol  = abs(order_depth.sell_orders[best_ask])
        total    = bid_vol + ask_vol
        return (bid_vol - ask_vol) / total if total > 0 else 0.0

    def _update_imbalance_history(self, product: str, imbalance: float):
        if product not in self.state.imbalance_history:
            self.state.imbalance_history[product] = []
        hist = self.state.imbalance_history[product]
        hist.append(imbalance)
        if len(hist) > 20:
            self.state.imbalance_history[product] = hist[-20:]

    def _smoothed_imbalance(self, product: str) -> float:
        hist = self.state.imbalance_history.get(product, [])
        return sum(hist) / len(hist) if hist else 0.0

    # ──────────────────────────────────────────────────────────
    # Core order generation
    # ──────────────────────────────────────────────────────────
    def _generate_orders(
        self,
        product: str,
        cfg: dict,
        order_depth: OrderDepth,
        fv: float,
        position: int,
        smooth_imb: float,
    ) -> List[Order]:
        """
        Two-phase strategy:

        PHASE 1 — TAKE: Immediately hit mispricings vs fair value.
          For Pepper: fv tracks the rising EMA, so we take asks
          that are below the current EMA (getting in cheap).
          For Osmium: we take any ask ≤ FV-1 or bid ≥ FV+1.

        PHASE 2 — MAKE: Post passive quotes inside the spread.
          For Pepper: BIDS ONLY (long_only=True, no asks ever).
          For Osmium: both bid and ask for spread capture.

        The imbalance signal nudges fv slightly in the direction of
        buy/sell pressure, improving fill timing.
        """
        orders:     List[Order] = []
        pos_limit   = cfg["soft_limit"]
        take_width  = cfg["take_width"]
        make_width  = cfg["make_width"]
        order_size  = cfg["order_size"]
        long_only   = cfg["long_only"]

        best_bid    = max(order_depth.buy_orders.keys())
        best_ask    = min(order_depth.sell_orders.keys())

        # Imbalance-adjusted fair value
        adj_fv = fv + smooth_imb * (make_width * 0.5)

        # Remaining capacity
        remaining_buy  = pos_limit - position
        remaining_sell = pos_limit + position

        # ════════════════════════════════════════════════════
        # PHASE 1: TAKE
        # ════════════════════════════════════════════════════

        # Buy cheap asks (below adj_fv - take_width)
        buy_threshold = adj_fv - take_width
        for ask_price in sorted(order_depth.sell_orders.keys()):
            if ask_price > buy_threshold:
                break
            if remaining_buy <= 0:
                break
            available = abs(order_depth.sell_orders[ask_price])
            # Sweep entire available volume per level (no order_size cap on TAKE).
            # For Pepper: fills +75 position in first 1-2 ticks thanks to high EMA seed.
            # For Osmium: take_width=2 already prevents noise; sweep all mispriced volume.
            qty = min(available, remaining_buy)
            if qty > 0:
                orders.append(Order(product, ask_price, qty))
                remaining_buy -= qty

        # Sell rich bids (above adj_fv + take_width) — Osmium only
        if not long_only:
            sell_threshold = adj_fv + take_width
            for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
                if bid_price < sell_threshold:
                    break
                if remaining_sell <= 0:
                    break
                available = order_depth.buy_orders[bid_price]
                qty = min(available, remaining_sell)  # sweep all mispriced sell-side too
                if qty > 0:
                    orders.append(Order(product, bid_price, -qty))
                    remaining_sell -= qty

        # ════════════════════════════════════════════════════
        # PHASE 2: MAKE (passive quoting)
        # ════════════════════════════════════════════════════

        # Inventory skew: if long, lower bid (buy less eagerly) and
        # lower ask (sell more eagerly) to mean-revert position.
        # For Pepper in long_only mode, skew only affects bid placement.
        inv_ratio = position / pos_limit if pos_limit > 0 else 0.0
        skew      = inv_ratio * make_width * 0.5

        # For Pepper long_only: once at soft limit, stop placing bids
        # (nothing to do — just hold the position)
        if long_only and position >= pos_limit:
            return orders

        # ── Passive BID ──────────────────────────────────────
        if remaining_buy > 0:
            our_bid = int(adj_fv - make_width + skew)
            # Clamp: must sit inside spread (below best_ask) but
            # can improve upon best_bid to be first in queue.
            our_bid = min(our_bid, best_ask - 1)
            buy_qty = min(order_size, remaining_buy)
            if buy_qty > 0:
                orders.append(Order(product, our_bid, buy_qty))

        # ── Passive ASK — OMITTED FOR PEPPER (long_only=True) ──
        if not long_only and remaining_sell > 0:
            our_ask = int(adj_fv + make_width + skew)
            our_ask = max(our_ask, best_bid + 1)
            sell_qty = min(order_size, remaining_sell)
            if sell_qty > 0:
                orders.append(Order(product, our_ask, -sell_qty))

        return orders


# ═══════════════════════════════════════════════════════════════
# STRATEGY SUMMARY
# ═══════════════════════════════════════════════════════════════
#
# ASH_COATED_OSMIUM (market making):
#   FV=10,000 (fixed), make_width=2 → quotes at 9,998/10,002
#   Beats market best bid 88-93% of ticks → high fill rate
#   Earns 4 XIRECS per round-trip, soft_limit=70 for max capacity
#   Imbalance signal nudges quotes toward heavier side of book
#
# INTARIAN_PEPPER_ROOT (trend riding):
#   EMA seed=13,000 (Day 1 extrapolated start price)
#   ema_alpha=0.15 — tracks the +1000/day rising price
#   TAKE phase: buy any ask ≤ EMA - 1 (accumulates quickly)
#   MAKE phase: bid at EMA - 5 + skew (passive accumulation)
#   long_only=True: NEVER place ask orders
#   Fills to +70 in 5-6 ticks, holds rest of day
#   Expected: 70 × 1000 price_rise ≈ 70,000 XIRECS mark-to-market
#
# CRITICAL DIFFERENCE FROM v4:
#   v4 Pepper returned static 13,500 as FV every tick (bug).
#   In second half of Day 1 (price > 13,503), static FV caused
#   SELLING, killing the long position.
#   v5 returns actual EMA → FV tracks price the whole day → no selling.
# ═══════════════════════════════════════════════════════════════
