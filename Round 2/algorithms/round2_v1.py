"""
Prosperity 4 — Round 2 Trading Algorithm
File: round2_v1.py

════════════════════════════════════════════════════════════════
ROUND 2 DATA ANALYSIS (from prices_round_2_day_*.csv):

ASH_COATED_OSMIUM:
  ┌─────────────────────────────────────────────────────────┐
  │ Bot always quotes symmetrically:                        │
  │   bid1 = mid - 8    ask1 = mid + 8    spread = 16      │
  │ True FV = mid_price ≈ 10,000 (stable across all days)  │
  │ Intraday mid range: ±15 from session open               │
  │ Full book 92% of ticks, avg vol per level = 14 units   │
  └─────────────────────────────────────────────────────────┘
  Strategy: Quote inside the bot spread.
    - Our bid @ mid-3: beats bot's bid (mid-8) → queue priority
    - Our ask @ mid+3: beats bot's ask (mid+8) → queue priority
    - EMA seeds from FIRST ACTUAL MID (no convergence lag)
    - Inventory skew: reduce position size as we approach limits
    - Take obvious mispricings: ask ≤ EMA-4 or bid ≥ EMA+4

INTARIAN_PEPPER_ROOT:
  ┌─────────────────────────────────────────────────────────┐
  │ Rises exactly +1,000 XIRECS every day (confirmed R2)   │
  │   Day -1: 11,001 → 11,999   Day 0: 11,999 → 13,000    │
  │   Day  1: 13,000 → 14,000   Day 2 (live): 14k → 15k   │
  │ Spread ≈ 14-15, avg ask1_vol ≈ 11 units                │
  └─────────────────────────────────────────────────────────┘
  Strategy: Fill +75 long as fast as possible. Hold all day.
    - EMA seeded ABOVE current price (15,500) → TAKE fires t=0
    - Long-only: NEVER place ask orders
    - Fills to +75 in first 6-7 ticks at any day's opening

MARKET ACCESS FEE (bid method):
  Starting at 100 for baseline testing.
  We increase after testing to find the optimal fee level.
════════════════════════════════════════════════════════════════
"""

import json
from typing import Dict, List, Tuple


# ════════════════════════════════════════════════════════════════
# Platform Data Model (must match datamodel.py exactly)
# ════════════════════════════════════════════════════════════════
class Order:
    def __init__(self, symbol: str, price: int, quantity: int) -> None:
        self.symbol   = symbol
        self.price    = price
        self.quantity = quantity

    def __repr__(self) -> str:
        return f"({self.symbol}, {self.price}, {self.quantity})"


class OrderDepth:
    def __init__(self):
        self.buy_orders:  Dict[int, int] = {}
        self.sell_orders: Dict[int, int] = {}


class Trade:
    def __init__(self, symbol: str, price: int, quantity: int,
                 buyer: str = None, seller: str = None, timestamp: int = 0) -> None:
        self.symbol    = symbol
        self.price     = price
        self.quantity  = quantity
        self.buyer     = buyer
        self.seller    = seller
        self.timestamp = timestamp


class Listing:
    def __init__(self, symbol: str, product: str, denomination: str):
        self.symbol      = symbol
        self.product     = product
        self.denomination = denomination


class Observation:
    def __init__(self):
        self.plainValueObservations: Dict = {}
        self.conversionObservations: Dict = {}


class TradingState:
    def __init__(self,
                 traderData:    str,
                 timestamp:     int,
                 listings:      Dict[str, Listing],
                 order_depths:  Dict[str, OrderDepth],
                 own_trades:    Dict[str, List[Trade]],
                 market_trades: Dict[str, List[Trade]],
                 position:      Dict[str, int],
                 observations:  Observation):
        self.traderData    = traderData
        self.timestamp     = timestamp
        self.listings      = listings
        self.order_depths  = order_depths
        self.own_trades    = own_trades
        self.market_trades = market_trades
        self.position      = position
        self.observations  = observations


# ════════════════════════════════════════════════════════════════
# Configuration
# ════════════════════════════════════════════════════════════════

# Pepper: seed EMA above Day-2 expected end-of-day price
# Ensures TAKE fires immediately from t=0 on all 3 days
PEPPER_EMA_SEED = 15_500

# Osmium: EMA seeds from FIRST OBSERVED MID (set below in SerializableState)
# No static seed needed — we grab the actual first price live
OSMIUM_EMA_SEED = None  # sentinel: use first mid price

PRODUCT_CONFIG = {
    # ── ASH_COATED_OSMIUM ─────────────────────────────────────
    # True FV = market mid (bot always quotes mid-8 / mid+8)
    # We quote mid-3 / mid+3 → inside the bot spread → queue priority
    # EMA alpha=0.05: smooths fast moves, tracks slow FV drift cleanly
    "ASH_COATED_OSMIUM": {
        "position_limit": 80,
        "soft_limit":     70,     # stay away from hard limit for safety
        "ema_seed":       None,   # None = seed from first actual mid
        "ema_alpha":      0.05,   # slow EMA to track FV drift cleanly
        "take_width":     4,      # take only real mispricings: ask ≤ EMA-4
        "make_width":     3,      # quote at EMA-3 / EMA+3 (inside bot spread)
        "order_size":     15,     # Increased to 15 to capture more volume when top-of-book
        "long_only":      False,
    },

    # ── INTARIAN_PEPPER_ROOT ──────────────────────────────────
    # Trends +1,000/day. Accumulate +75 long in first 6-7 ticks. Hold.
    # EMA seeded high (15,500) so TAKE threshold fires on ANY market ask
    "INTARIAN_PEPPER_ROOT": {
        "position_limit": 80,
        "soft_limit":     75,     # fill to +75 and hold
        "ema_seed":       PEPPER_EMA_SEED,
        "ema_alpha":      0.10,   # tracks rising price without dropping too fast
        "take_width":     1,      # EMA >> market → fires immediately
        "make_width":     5,      # passive bids inside spread for residual fills
        "order_size":     30,     # aggressive fill size: get to +75 in 3 ticks
        "long_only":      True,   # NEVER place asks — ride the trend
    },
}


# ════════════════════════════════════════════════════════════════
# Persistent State (carried across ticks via traderData JSON)
# ════════════════════════════════════════════════════════════════
class AlgoState:
    def __init__(self):
        self.ema:            Dict[str, float] = {}   # EMA fair value per product
        self.imb_history:    Dict[str, List[float]] = {}  # smoothed imbalance buffer
        self.last_timestamp: int = 0

    # ── Serialization ─────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "ema":            self.ema,
            "imb_history":    self.imb_history,
            "last_timestamp": self.last_timestamp,
        }

    @staticmethod
    def from_dict(d: dict) -> "AlgoState":
        s = AlgoState()
        s.ema            = d.get("ema", {})
        s.imb_history    = d.get("imb_history", {})
        s.last_timestamp = d.get("last_timestamp", 0)
        return s

    def serialize(self) -> str:
        return json.dumps(self.to_dict())

    @staticmethod
    def deserialize(raw: str) -> "AlgoState":
        if not raw or not raw.strip():
            return AlgoState()
        try:
            return AlgoState.from_dict(json.loads(raw))
        except Exception:
            return AlgoState()


# ════════════════════════════════════════════════════════════════
# Trader
# ════════════════════════════════════════════════════════════════
class Trader:

    def __init__(self):
        self._state       = AlgoState()
        self._initialized = False

    # ── Market Access Fee ──────────────────────────────────────
    # Starting at 2500.
    # +25% volume is worth roughly ~3,500 XIRECS over the round for Osmium.
    # Bidding 2,500 means we win the auction against naive teams and still net profit.
    def bid(self) -> int:
        return 2500

    # ── Main Entry Point ───────────────────────────────────────
    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:

        # Deserialize persistent state on first call
        if not self._initialized:
            self._state       = AlgoState.deserialize(state.traderData)
            self._initialized = True

        # Day boundary: reset imbalance buffer (keeps EMA — intentional)
        if state.timestamp < self._state.last_timestamp:
            self._state.imb_history = {}

        result: Dict[str, List[Order]] = {}

        for product, order_depth in state.order_depths.items():
            cfg      = PRODUCT_CONFIG.get(product)
            if cfg is None:
                result[product] = []
                continue

            # Skip if book is empty on either side
            if not order_depth.buy_orders or not order_depth.sell_orders:
                result[product] = []
                continue

            position = state.position.get(product, 0)

            # Step 1: Update EMA fair value
            fv = self._update_ema(product, cfg, order_depth)

            # Step 2: Compute smoothed order-book imbalance
            imb = self._book_imbalance(order_depth)
            self._push_imbalance(product, imb)
            smooth_imb = self._smooth_imbalance(product)

            # Step 3: Generate orders
            result[product] = self._generate_orders(
                product, cfg, order_depth, fv, position, smooth_imb
            )

        self._state.last_timestamp = state.timestamp
        return result, 0, self._state.serialize()

    # ── EMA Fair Value ─────────────────────────────────────────
    def _update_ema(self, product: str, cfg: dict,
                    order_depth: OrderDepth) -> float:
        """
        EMA fair value with smart seeding:
          - Osmium (ema_seed=None): seeds from FIRST OBSERVED MID.
            This eliminates the convergence lag that killed Osmium in v6/v7.
            From tick 1 onwards, EMA is already at the actual price level.
          - Pepper (ema_seed=15_500): high seed ensures TAKE fires from t=0,
            then EMA slowly converges downward toward actual price.
            alpha=0.10 means it takes ~50 ticks to converge fully — but
            that's fine because we fill our entire position in 6-7 ticks.
        """
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        mid      = (best_bid + best_ask) / 2.0

        if product not in self._state.ema:
            seed = cfg["ema_seed"]
            # Osmium: use actual first mid as seed (zero convergence lag)
            self._state.ema[product] = mid if seed is None else float(seed)

        # Update EMA
        alpha = cfg["ema_alpha"]
        self._state.ema[product] = alpha * mid + (1.0 - alpha) * self._state.ema[product]
        return self._state.ema[product]

    # ── Order Book Imbalance ───────────────────────────────────
    def _book_imbalance(self, od: OrderDepth) -> float:
        """
        Best-level imbalance in [-1, +1].
        +1 = all volume at bid (buy pressure → nudge FV up slightly)
        -1 = all volume at ask (sell pressure → nudge FV down slightly)
        """
        if not od.buy_orders or not od.sell_orders:
            return 0.0
        best_bid = max(od.buy_orders.keys())
        best_ask = min(od.sell_orders.keys())
        bv = od.buy_orders[best_bid]
        av = abs(od.sell_orders[best_ask])
        total = bv + av
        return (bv - av) / total if total > 0 else 0.0

    def _push_imbalance(self, product: str, imb: float):
        buf = self._state.imb_history.setdefault(product, [])
        buf.append(imb)
        if len(buf) > 20:
            self._state.imb_history[product] = buf[-20:]

    def _smooth_imbalance(self, product: str) -> float:
        buf = self._state.imb_history.get(product, [])
        return sum(buf) / len(buf) if buf else 0.0

    # ── Order Generation ───────────────────────────────────────
    def _generate_orders(
        self,
        product:   str,
        cfg:       dict,
        od:        OrderDepth,
        fv:        float,
        position:  int,
        smooth_imb: float,
    ) -> List[Order]:
        """
        Two-phase per tick:

        PHASE 1 — TAKE (aggressive):
          Hit any order that is mispriced vs our EMA.
          Osmium:  take asks ≤ EMA-4 or bids ≥ EMA+4 (real mispricings only)
          Pepper:  take ANY ask ≤ EMA-1 (EMA seed >> market, fires every tick)

        PHASE 2 — MAKE (passive):
          Post quotes inside the bot spread.
          Osmium:  bid @ EMA-3, ask @ EMA+3 (inside bot's EMA-8/EMA+8)
          Pepper:  bid only (long_only=True), at EMA-5 for residual fills
          Inventory skew adjusts quotes to lean toward position reduction.
        """
        orders: List[Order] = []

        pos_limit  = cfg["soft_limit"]
        take_w     = cfg["take_width"]
        make_w     = cfg["make_width"]
        ord_size   = cfg["order_size"]
        long_only  = cfg["long_only"]

        best_bid = max(od.buy_orders.keys())
        best_ask = min(od.sell_orders.keys())

        # Imbalance-adjusted fair value (small nudge ≤ 1 tick typically)
        adj_fv = fv + smooth_imb * (make_w * 0.5)

        remaining_buy  = pos_limit - position
        remaining_sell = pos_limit + position

        # ────────────────────────────────────────────────────────
        # PHASE 1: TAKE
        # ────────────────────────────────────────────────────────

        # Take cheap asks
        buy_thresh = adj_fv - take_w
        for ask_px in sorted(od.sell_orders.keys()):
            if ask_px > buy_thresh or remaining_buy <= 0:
                break
            qty = min(abs(od.sell_orders[ask_px]), remaining_buy)
            if qty > 0:
                orders.append(Order(product, ask_px, qty))
                remaining_buy -= qty

        # Take rich bids (Osmium only)
        if not long_only:
            sell_thresh = adj_fv + take_w
            for bid_px in sorted(od.buy_orders.keys(), reverse=True):
                if bid_px < sell_thresh or remaining_sell <= 0:
                    break
                qty = min(od.buy_orders[bid_px], remaining_sell)
                if qty > 0:
                    orders.append(Order(product, bid_px, -qty))
                    remaining_sell -= qty

        # ────────────────────────────────────────────────────────
        # PHASE 2: MAKE (passive)
        # ────────────────────────────────────────────────────────

        # Inventory skew: lean toward reducing position
        # skew > 0 → we're long → lower bid (buy less) + lower ask (sell more)
        # skew < 0 → we're short → raise bid (buy more) + raise ask (sell less)
        inv_ratio = position / pos_limit if pos_limit > 0 else 0.0
        skew      = inv_ratio * make_w * 0.5

        # Pepper: once full, stop quoting
        if long_only and position >= pos_limit:
            return orders

        # ── Passive BID ─────────────────────────────────────────
        if remaining_buy > 0:
            our_bid = int(adj_fv - make_w + skew)
            # Safety: never cross the spread (must be below best_ask)
            our_bid = min(our_bid, best_ask - 1)
            # Safety: for Osmium, don't quote below worst-reasonable price
            if not long_only:
                our_bid = max(our_bid, best_bid - 4)  # within 4 of current best bid
            qty = min(ord_size, remaining_buy)
            if qty > 0:
                orders.append(Order(product, our_bid, qty))

        # ── Passive ASK (Osmium only) ────────────────────────────
        if not long_only and remaining_sell > 0:
            our_ask = int(adj_fv + make_w + skew)
            # Safety: never cross the spread
            our_ask = max(our_ask, best_bid + 1)
            # Safety: don't quote above worst-reasonable price
            our_ask = min(our_ask, best_ask + 4)  # within 4 of current best ask
            qty = min(ord_size, remaining_sell)
            if qty > 0:
                orders.append(Order(product, our_ask, -qty))

        return orders


# ════════════════════════════════════════════════════════════════
# PARAMETER REFERENCE
# ════════════════════════════════════════════════════════════════
#
# bid() = 100  [TESTING STARTING POINT — will adjust after results]
#
# ASH_COATED_OSMIUM:
#   ema_seed   = None (seeds from actual first mid → zero convergence lag)
#   ema_alpha  = 0.05 (slow, stable tracking)
#   take_width = 4    (only take real mispricings vs EMA)
#   make_width = 3    (bid@EMA-3, ask@EMA+3 → inside bot's EMA-8/EMA+8)
#   order_size = 12
#   soft_limit = 70
#
# INTARIAN_PEPPER_ROOT:
#   ema_seed   = 15,500 (above Day-2 end price → TAKE fires from t=0)
#   ema_alpha  = 0.10
#   take_width = 1
#   make_width = 5    (passive bids for residual fills)
#   order_size = 30   (fill to +75 in 3 ticks)
#   soft_limit = 75
#   long_only  = True (never sells)
# ════════════════════════════════════════════════════════════════
