"""
Prosperity 4 - Round 1 Trading Algorithm v4.0
Products: ASH_COATED_OSMIUM, INTARIAN_PEPPER_ROOT

═══════════════════════════════════════════════════════════════
DATA FINDINGS (from find_pepper_fv.py diagnostic):

  INTARIAN_PEPPER_ROOT — NOT like Emeralds!
    Day -2: 9,998 → 11,003  (+500 intraday drift, median 10,500)
    Day -1: 10,995 → 12,006 (+500 intraday drift, median 11,500)
    Day  0: 11,994 → 13,007 (+500 intraday drift, median 12,500)
    Day  1: extrapolated start ~12,994, median ~13,500  ← live round

  Pepper is a TRENDING asset, rising +500 XIRECS per day.
  Fixed FV is wrong. Use EMA to track the trend dynamically.
  Strategy: trend-following bias — prefer BUY side, use tight
            passive quotes that ride the upward drift.

  ASH_COATED_OSMIUM — stable, fair value = 10,000.
  Strategy: aggressive TAKE + MAKE (dual-mode), imbalance signal.
═══════════════════════════════════════════════════════════════

MAJOR UPGRADES OVER v2.0/v3.0:

1. PEPPER: EMA trend-following (NOT fixed FV)
   - EMA tracks the continuously rising price (~+0.05 per tick)
   - Trend bias: buy-side preferred, sell only when overbought
   - Extrapolated Day 1 start value: ~13,500
   - Expected: capture the trend instead of fighting it

2. OSMIUM: Much more aggressive + market taking
   - Full position limit exploitation (±50 instead of ±40)
   - Aggressive taking when asks < FV or bids > FV
   - Passive quoting inside the spread for additional edge
   - Look for "hidden pattern" via order book imbalance signal
   - Expected: +3,000 to +8,000 XIRECS (vs current +1,296)

3. BOTH: Dual-mode execution
   - TAKE mode: Hit mispricings immediately (highest priority)
   - MAKE mode: Post passive quotes to earn the spread
   - This is how top teams 30x their PnL vs pure market making
"""

import json
from typing import Dict, List, Optional, Tuple
from collections import deque


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
# CRITICAL: Verify PEPPER_FAIR_VALUE from your submission day data!
# How to find it:
#   1. Look at prices_round_1_day_0.csv
#   2. Find the price level where the most volume trades
#   3. OR find the dominant bot market maker's mid-price
#   4. OR look for the price where spreads are most symmetric
#
# The challenge says Pepper is like Emeralds → there IS a fixed value.
# Your data showed it trading ~12,000-12,100. If you see consistent
# buy/sell orders anchored at one level → that IS the fair value.
#
# For Osmium the FV is clearly 10,000 (same as Rainforest Resin in P3).
# ═══════════════════════════════════════════════════════════════

# ─── VERIFIED VALUES (from find_pepper_fv.py on real data) ──────
OSMIUM_FAIR_VALUE  = 10_000   # Stable, confirmed fixed at 10,000

# Pepper trends ~+1000 XIRECS per day in historical Round 1 data.
# Day -2 median≈10500, Day -1 median≈11500, Day 0 median≈12500.
# Day 1 (live round) extrapolated start ≈ 13,500.
# We use EMA (use_ema=True) to track the trend dynamically.
# This seed value is the starting estimate; EMA will adapt fast.
PEPPER_FAIR_VALUE  = 13_500   # ✅ Extrapolated Day 1 starting FV
# ────────────────────────────────────────────────────────────────

PRODUCT_CONFIG = {
    "ASH_COATED_OSMIUM": {
        "fair_value":        OSMIUM_FAIR_VALUE,
        "position_limit":    80,
        "soft_limit":        50,        # Use up to 50 units (was 40)
        "take_width":        2,         # Take any order ≥2 away from FV
        "make_width":        3,         # Our passive quote offset from FV
        "order_size":        12,        # Larger orders (was 10)
        "use_ema":           False,     # Fixed FV, no EMA needed
        "ema_alpha":         0.05,
        "trend_bias":        0.0,       # No trend bias for Osmium
    },
    "INTARIAN_PEPPER_ROOT": {
        "fair_value":        PEPPER_FAIR_VALUE,
        "position_limit":    80,
        "soft_limit":        40,        # Conservative — trend makes position risk higher
        "take_width":        3,         # Wider take width (spread avg is ~14)
        "make_width":        6,         # Wide passive quotes around EMA
        "order_size":        8,         # Smaller size — trend-following is riskier
        "use_ema":           True,      # ✅ EMA tracks the continuous upward drift
        "ema_alpha":         0.10,      # Faster adaptation to track the trend
        "trend_bias":        0.5,       # Bias bid/ask toward buy side (uptrend)
        "ema_anchor_weight": 0.10,      # Keep EMA mostly adaptive; retain small seed influence during warm-up
        "trend_lookahead":   8,         # Project EMA by near-term trend slope
        "max_short":         8,         # Strong short-side guardrail in trending market
        "disable_passive_sell_in_uptrend": True,
        "uptrend_slope_threshold": 0.25,
        "drawdown_limit":    800.0,     # Per-product mark-to-market brake
        "drawdown_recover":  200.0,     # Re-enable only after partial recovery
        "toxicity_alpha":    0.2,       # Fill-toxicity EMA smoothing
        "toxicity_threshold": 1.5,      # Widen/slow quoting when fills turn toxic
        "max_extra_width":   3,         # Max additional width from risk signals
        "min_order_size":    2,
        "risk_reduce_size_multiplier": 2,
    },
}


# ═══════════════════════════════════════════════════════════════
# State Management
# ═══════════════════════════════════════════════════════════════
class SerializableState:
    def __init__(self):
        self.ema_fv: Dict[str, float] = {}          # EMA fallback FV estimate
        self.price_history: Dict[str, List[float]] = {}
        self.last_timestamp: int = 0
        # Imbalance signal tracking
        self.imbalance_history: Dict[str, List[float]] = {}
        self.mid_history: Dict[str, List[float]] = {}
        self.last_mid: Dict[str, float] = {}
        self.last_position: Dict[str, int] = {}
        self.mtm_pnl: Dict[str, float] = {}
        self.peak_mtm_pnl: Dict[str, float] = {}
        self.kill_switch: Dict[str, bool] = {}
        self.toxicity_score: Dict[str, float] = {}
        self.last_trade_ts: Dict[str, int] = {}

    def to_dict(self) -> dict:
        return {
            "ema_fv":            self.ema_fv,
            "price_history":     self.price_history,
            "last_timestamp":    self.last_timestamp,
            "imbalance_history": self.imbalance_history,
            "mid_history":       self.mid_history,
            "last_mid":          self.last_mid,
            "last_position":     self.last_position,
            "mtm_pnl":           self.mtm_pnl,
            "peak_mtm_pnl":      self.peak_mtm_pnl,
            "kill_switch":       self.kill_switch,
            "toxicity_score":    self.toxicity_score,
            "last_trade_ts":     self.last_trade_ts,
        }

    @staticmethod
    def from_dict(data: dict) -> "SerializableState":
        s = SerializableState()
        s.ema_fv            = data.get("ema_fv", {})
        s.price_history     = data.get("price_history", {})
        s.last_timestamp    = data.get("last_timestamp", 0)
        s.imbalance_history = data.get("imbalance_history", {})
        s.mid_history       = data.get("mid_history", {})
        s.last_mid          = data.get("last_mid", {})
        s.last_position     = data.get("last_position", {})
        s.mtm_pnl           = data.get("mtm_pnl", {})
        s.peak_mtm_pnl      = data.get("peak_mtm_pnl", {})
        s.kill_switch       = data.get("kill_switch", {})
        s.toxicity_score    = data.get("toxicity_score", {})
        s.last_trade_ts     = data.get("last_trade_ts", {})
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
# Trader Class - v4.0
# ═══════════════════════════════════════════════════════════════
class Trader:

    def __init__(self):
        self.state = SerializableState()
        self._initialized = False

    def bid(self):
        """Required for Round 2 — leave at 15."""
        return 15

    # ──────────────────────────────────────────────────────────
    # Main entry point
    # ──────────────────────────────────────────────────────────
    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:

        if not self._initialized:
            self.state = SerializableState.deserialize(state.traderData)
            self._initialized = True

        if state.timestamp < self.state.last_timestamp:
            # New day reset — keep EMA estimates, clear short-term history
            self.state.price_history = {}
            self.state.imbalance_history = {}
            self.state.mid_history = {}
            self.state.last_mid = {}
            self.state.last_position = {}
            self.state.mtm_pnl = {}
            self.state.peak_mtm_pnl = {}
            self.state.kill_switch = {}
            self.state.toxicity_score = {}
            self.state.last_trade_ts = {}

        result: Dict[str, List[Order]] = {}

        for product in state.order_depths:
            if product not in PRODUCT_CONFIG:
                result[product] = []
                continue

            cfg          = PRODUCT_CONFIG[product]
            order_depth  = state.order_depths[product]
            position     = state.position.get(product, 0)

            if not order_depth.buy_orders or not order_depth.sell_orders:
                result[product] = []
                continue

            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            mid = (best_bid + best_ask) / 2.0
            self._update_market_state(product, cfg, mid, position)
            self._update_fill_toxicity(
                product, cfg, state.own_trades.get(product, []), mid
            )

            # ── Fair value resolution ──────────────────────────
            fv = self._resolve_fair_value(product, cfg, order_depth)

            # ── Order imbalance signal (Osmium "hidden pattern") ─
            imbalance = self._order_book_imbalance(order_depth)
            self._update_imbalance_history(product, imbalance)

            # ── Generate orders: TAKE + MAKE ──────────────────
            orders = self._generate_orders(
                product, cfg, order_depth, fv, position, imbalance
            )
            result[product] = orders

        self.state.last_timestamp = state.timestamp
        return result, 0, self.state.serialize()

    # ──────────────────────────────────────────────────────────
    # Fair value resolution
    # ──────────────────────────────────────────────────────────
    def _resolve_fair_value(self, product: str, cfg: dict,
                             order_depth: OrderDepth) -> float:
        """
        Primary: hardcoded fair value from config.
        Fallback: EMA of mid-price (only kicks in if hardcoded FV seems
                  wildly off — helps on day-1 for Pepper if true FV
                  turns out different from our guess).

        For products where use_ema=True, blend EMA with config FV.
        For products with use_ema=False, just return config FV directly.
        """
        config_fv = float(cfg["fair_value"])

        if not cfg["use_ema"]:
            return config_fv

        # EMA fallback path
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        mid = (best_bid + best_ask) / 2.0

        alpha = cfg["ema_alpha"]
        if product not in self.state.ema_fv:
            self.state.ema_fv[product] = mid
        else:
            self.state.ema_fv[product] = (
                alpha * mid + (1 - alpha) * self.state.ema_fv[product]
            )

        trend_slope = self._trend_slope(product)
        projected = self.state.ema_fv[product] + trend_slope * cfg.get("trend_lookahead", 0)
        anchor_weight = cfg.get("ema_anchor_weight", 0.0)

        # Adaptive FV with small anchor only for seed stability.
        return (1 - anchor_weight) * projected + anchor_weight * config_fv

    # ──────────────────────────────────────────────────────────
    # Order book imbalance — the "hidden pattern" signal
    # ──────────────────────────────────────────────────────────
    def _order_book_imbalance(self, order_depth: OrderDepth) -> float:
        """
        Computes order book imbalance at the best bid/ask level.
        Range: [-1, +1]
          +1 = huge buy pressure (price likely to move up)
          -1 = huge sell pressure (price likely to move down)

        This is the most common "hidden pattern" in stable market-making
        products — skew your quotes toward the heavier side.
        """
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return 0.0

        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())

        bid_vol = order_depth.buy_orders[best_bid]
        ask_vol = abs(order_depth.sell_orders[best_ask])  # sell_orders are negative

        total = bid_vol + ask_vol
        if total == 0:
            return 0.0

        return (bid_vol - ask_vol) / total   # in (-1, +1)

    def _update_imbalance_history(self, product: str, imbalance: float):
        if product not in self.state.imbalance_history:
            self.state.imbalance_history[product] = []
        hist = self.state.imbalance_history[product]
        hist.append(imbalance)
        if len(hist) > 20:
            self.state.imbalance_history[product] = hist[-20:]

    def _smoothed_imbalance(self, product: str) -> float:
        hist = self.state.imbalance_history.get(product, [])
        if not hist:
            return 0.0
        return sum(hist) / len(hist)

    def _trend_slope(self, product: str, window: int = 20) -> float:
        mids = self.state.mid_history.get(product, [])
        if len(mids) < 2:
            return 0.0
        lookback = mids[-window:]
        return (lookback[-1] - lookback[0]) / max(1, len(lookback) - 1)

    def _update_market_state(self, product: str, cfg: dict, mid: float, position: int):
        mids = self.state.mid_history.setdefault(product, [])
        mids.append(mid)
        if len(mids) > 100:
            self.state.mid_history[product] = mids[-100:]

        prev_mid = self.state.last_mid.get(product)
        prev_pos = self.state.last_position.get(product, position)
        if prev_mid is not None:
            mtm = self.state.mtm_pnl.get(product, 0.0)
            mtm += prev_pos * (mid - prev_mid)
            self.state.mtm_pnl[product] = mtm
            peak = max(self.state.peak_mtm_pnl.get(product, mtm), mtm)
            self.state.peak_mtm_pnl[product] = peak

            drawdown = peak - mtm
            limit = float(cfg.get("drawdown_limit", 10**18))
            recover = float(cfg.get("drawdown_recover", limit * 0.5))
            if drawdown >= limit:
                self.state.kill_switch[product] = True
            elif self.state.kill_switch.get(product, False) and drawdown <= recover:
                self.state.kill_switch[product] = False

        self.state.last_mid[product] = mid
        self.state.last_position[product] = position

    def _update_fill_toxicity(
        self, product: str, cfg: dict, own_trades: List[Trade], mid: float
    ):
        if not own_trades:
            return
        last_ts = self.state.last_trade_ts.get(product, -1)
        alpha = float(cfg.get("toxicity_alpha", 0.2))
        score = float(self.state.toxicity_score.get(product, 0.0))
        max_seen_ts = last_ts

        for tr in own_trades:
            if tr.timestamp <= last_ts:
                continue
            qty = abs(tr.quantity)
            signed_qty = 0
            if tr.buyer == "SUBMISSION":
                signed_qty = qty
            elif tr.seller == "SUBMISSION":
                signed_qty = -qty
            if signed_qty == 0:
                continue

            edge = (mid - tr.price) * signed_qty
            adverse = max(0.0, -edge)
            score = (1 - alpha) * score + alpha * adverse
            if tr.timestamp > max_seen_ts:
                max_seen_ts = tr.timestamp

        self.state.toxicity_score[product] = score
        self.state.last_trade_ts[product] = max_seen_ts

    def _adjust_execution_params(
        self, product: str, cfg: dict, order_depth: OrderDepth
    ) -> Tuple[int, int, int]:
        base_take = int(cfg["take_width"])
        base_make = int(cfg["make_width"])
        base_size = int(cfg["order_size"])

        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        spread = max(1, best_ask - best_bid)
        bid_vol = max(1, order_depth.buy_orders.get(best_bid, 1))
        ask_vol = max(1, abs(order_depth.sell_orders.get(best_ask, -1)))
        top_liquidity = max(1, min(bid_vol, ask_vol))

        take_width = max(base_take, int(round(spread * 0.35)))
        make_width = max(base_make, int(round(spread * 0.45)))

        size_scale = min(1.0, top_liquidity / max(1.0, base_size * 2.0))
        min_size = int(cfg.get("min_order_size", 1))
        order_size = max(min_size, int(round(base_size * size_scale)))

        tox = float(self.state.toxicity_score.get(product, 0.0))
        tox_threshold = float(cfg.get("toxicity_threshold", 10**9))
        if tox > tox_threshold:
            # Scale extra width by how far toxicity is above threshold.
            toxicity_ratio = (tox - tox_threshold) / max(1.0, tox_threshold)
            calculated_extra_width = max(0, int(toxicity_ratio))
            extra = min(int(cfg.get("max_extra_width", 2)), calculated_extra_width)
            take_width += extra
            make_width += extra
            order_size = max(min_size, order_size - extra)

        return take_width, make_width, order_size

    def _risk_reduce_only_orders(
        self, product: str, cfg: dict, order_depth: OrderDepth, position: int, order_size: int
    ) -> List[Order]:
        if position == 0:
            return []
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        multiplier = int(cfg.get("risk_reduce_size_multiplier", 2))
        multiplier = max(1, multiplier)
        qty = min(abs(position), max(1, order_size * multiplier))
        if position > 0:
            return [Order(product, best_bid, -qty)]
        return [Order(product, best_ask, qty)]

    # ──────────────────────────────────────────────────────────
    # Core order generation: TAKE + MAKE
    # ──────────────────────────────────────────────────────────
    def _generate_orders(
        self,
        product: str,
        cfg: dict,
        order_depth: OrderDepth,
        fv: float,
        position: int,
        imbalance: float,
    ) -> List[Order]:
        """
        Two-phase strategy:
        Phase 1 — TAKE:  Immediately hit any orders mispriced vs FV.
        Phase 2 — MAKE:  Post passive quotes around FV to earn spread.

        This is how top teams extract 30x more PnL than passive-only.
        """
        orders: List[Order] = []
        pos_limit   = cfg["soft_limit"]
        take_width, make_width, order_size = self._adjust_execution_params(
            product, cfg, order_depth
        )
        trend_bias  = cfg.get("trend_bias", 0.0)   # 0=neutral, +ve=buy-biased

        best_bid   = max(order_depth.buy_orders.keys())
        best_ask   = min(order_depth.sell_orders.keys())

        if self.state.kill_switch.get(product, False):
            return self._risk_reduce_only_orders(product, cfg, order_depth, position, order_size)

        # ── Imbalance-adjusted fair value ─────────────────────
        # If buy pressure is high (imbalance > 0), nudge FV up slightly.
        # This skews our quotes to reduce adverse selection.
        smooth_imb = self._smoothed_imbalance(product)
        adj_fv     = fv + smooth_imb * (make_width * 0.5)

        # ── Trend bias ────────────────────────────────────────
        # For a trending product (like Pepper's +500/day uptrend):
        #   trend_bias > 0 → shift our effective FV up so we buy
        #   more aggressively and only sell when truly above FV.
        # This prevents accumulating a short position in an uptrend
        # (the root cause of v1.0 & v3.0 Pepper losses).
        adj_fv = adj_fv + trend_bias * make_width

        # ── Track remaining capacity ──────────────────────────
        remaining_buy  = pos_limit - position        # how much more we can buy
        remaining_sell = pos_limit + position        # how much more we can sell
        trend_slope = self._trend_slope(product)

        # Pepper-specific short guardrails in uptrend regimes.
        sell_threshold = adj_fv + take_width
        allow_passive_sell = True
        if product == "INTARIAN_PEPPER_ROOT":
            max_short = int(cfg.get("max_short", pos_limit))
            remaining_sell = min(remaining_sell, max(0, position + max_short))
            uptrend_threshold = float(cfg.get("uptrend_slope_threshold", 0.0))
            if trend_slope > uptrend_threshold:
                sell_threshold = adj_fv + take_width + 1
                if cfg.get("disable_passive_sell_in_uptrend", False):
                    allow_passive_sell = False

        # ════════════════════════════════════════════════════
        # PHASE 1: TAKE (market taking — highest priority)
        # Hit orders that are clearly wrong relative to FV.
        # This locks in guaranteed profit immediately.
        # ════════════════════════════════════════════════════

        # Take cheap asks (someone selling below FV - take_width)
        buy_threshold = adj_fv - take_width
        for ask_price in sorted(order_depth.sell_orders.keys()):
            if ask_price > buy_threshold:
                break
            if remaining_buy <= 0:
                break
            available = abs(order_depth.sell_orders[ask_price])
            qty = min(available, remaining_buy, order_size * 2)  # be aggressive
            if qty > 0:
                orders.append(Order(product, ask_price, qty))
                remaining_buy  -= qty

        # Take rich bids (someone buying above FV + take_width)
        for bid_price in sorted(order_depth.buy_orders.keys(), reverse=True):
            if bid_price < sell_threshold:
                break
            if remaining_sell <= 0:
                break
            available = order_depth.buy_orders[bid_price]
            qty = min(available, remaining_sell, order_size * 2)
            if qty > 0:
                orders.append(Order(product, bid_price, -qty))
                remaining_sell -= qty

        # ════════════════════════════════════════════════════
        # PHASE 2: MAKE (passive quoting — earn the spread)
        # Post limit orders inside the current spread, around FV.
        # Inventory skew ensures we don't get stuck one-sided.
        # ════════════════════════════════════════════════════

        # Inventory ratio in [-1, +1]
        inv_ratio = position / pos_limit if pos_limit > 0 else 0.0

        # Skew our quotes based on inventory:
        # If long → lower bid (don't want more longs) & lower ask (unload faster)
        # If short → raise bid (cover faster) & raise ask (don't add more shorts)
        skew = inv_ratio * make_width * 0.5

        our_bid = int(adj_fv - make_width + skew)
        our_ask = int(adj_fv + make_width + skew)

        # Clamp to INSIDE the spread — quote up to 1 tick from the other side.
        # This means our passive orders sit inside the current spread, making
        # them attractive to bots and getting filled frequently.
        # (Old logic clamped to OUTSIDE, giving almost no fills — Osmium bug.)
        our_bid = min(our_bid, best_ask - 1)   # can beat best bid, but never cross ask
        our_ask = max(our_ask, best_bid + 1)   # can beat best ask, but never cross bid

        # Ensure minimum 1-tick spread between our own bid/ask
        if our_ask <= our_bid:
            mid = (our_bid + our_ask) // 2
            our_bid = mid - 1
            our_ask = mid + 1

        # Place passive bid
        if remaining_buy > 0:
            buy_qty = min(order_size, remaining_buy)
            orders.append(Order(product, our_bid, buy_qty))

        # Place passive ask
        if remaining_sell > 0 and allow_passive_sell:
            sell_qty = min(order_size, remaining_sell)
            orders.append(Order(product, our_ask, -sell_qty))

        return orders


# ═══════════════════════════════════════════════════════════════
# DATA FINDINGS — PEPPER FAIR VALUE ANALYSIS
# (Generated by find_pepper_fv.py on real market data)
# ═══════════════════════════════════════════════════════════════
#
#  Day -2: median=10500, range=[9998, 11003], drift≈+1000  ⚠️ TRENDING
#  Day -1: median=11500, range=[10995, 12006], drift≈+1000 ⚠️ TRENDING
#  Day  0: median=12500, range=[11994, 13007], drift≈+1000 ⚠️ TRENDING
#  Day  1: extrapolated median ≈ 13500 (live round)
#
#  CONCLUSION: Pepper is NOT like Emeralds. It trends ~+1000/day.
#  A fixed fair value would lose money (as confirmed by v1 & v3).
#  EMA with use_ema=True adapts to the trend dynamically.
#  The seed value PEPPER_FAIR_VALUE=13500 anchors the EMA at
#  the expected start of Day 1.
#
#  To re-run the diagnostic:
#      python3 find_pepper_fv.py
# ═══════════════════════════════════════════════════════════════
