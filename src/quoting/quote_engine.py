from dataclasses import dataclass

from src.config import (
    INITIAL_INVENTORY,
    MAX_LONG_INVENTORY,
    MAX_SHORT_INVENTORY,
    QUOTE_BASE_SIZE,
    QUOTE_DEGRADED_SIZE_MULTIPLIER,
    QUOTE_DEGRADED_SPREAD_MULTIPLIER,
    QUOTE_DISAGREEMENT_SPREAD_PER_BPS,
    QUOTE_INVENTORY_SKEW,
    QUOTE_LIQUIDITY_PARTICIPATION,
    QUOTE_MARKET_EDGE_BUFFER,
    QUOTE_MIN_ABSOLUTE_SIZE,
    QUOTE_MIN_HALF_SPREAD,
    QUOTE_MIN_SIZE_FACTOR,
    QUOTE_SIZE_DEGRADED_MULTIPLIER,
    QUOTE_SIZE_HEALTHY_MULTIPLIER,
    QUOTE_SIZE_MAX_DISAGREEMENT_BPS,
    QUOTE_SIZE_MIN_DISAGREEMENT_FACTOR,
    QUOTE_SIZE_MIN_SPREAD_FACTOR,
    QUOTE_SIZE_SPREAD_TARGET_BPS,
    QUOTE_SIZE_UNHEALTHY_MULTIPLIER,
    QUOTE_SUPPRESS_CROSSED_MARKET,
    QUOTE_SUPPRESS_MAX_DISAGREEMENT_BPS,
    QUOTE_SUPPRESS_SINGLE_LOW_CONFIDENCE,
)
from src.fair_value.fair_value import FairValueResult, VenueQuote


@dataclass
class QuoteRecommendation:
    reservation_price: float | None

    bid_price: float | None
    bid_size: float | None
    ask_price: float | None
    ask_size: float | None

    inventory: float
    status: str

    raw_size: float | None = None
    liquidity_cap: float | None = None
    health_factor: float | None = None
    spread_factor: float | None = None
    disagreement_factor: float | None = None
    bid_size_factor: float | None = None
    ask_size_factor: float | None = None
    half_spread: float | None = None


class QuoteEngine:
    def __init__(
        self,
        base_size: float = QUOTE_BASE_SIZE,
        min_half_spread: float = QUOTE_MIN_HALF_SPREAD,
        inventory_skew: float = QUOTE_INVENTORY_SKEW,
        inventory: float = INITIAL_INVENTORY,
        max_long_inventory: float = MAX_LONG_INVENTORY,
        max_short_inventory: float = MAX_SHORT_INVENTORY,
    ) -> None:
        self.base_size = base_size
        self.min_half_spread = min_half_spread
        self.inventory_skew = inventory_skew
        self.inventory = inventory
        self.max_long_inventory = max_long_inventory
        self.max_short_inventory = max_short_inventory

    def _inventory_utilization(self) -> float:
        if self.inventory >= 0 and self.max_long_inventory > 0:
            utilization = self.inventory / self.max_long_inventory
        elif self.inventory < 0 and self.max_short_inventory < 0:
            utilization = self.inventory / abs(self.max_short_inventory)
        else:
            utilization = 0.0

        return min(max(utilization, -1.0), 1.0)

    def _should_suppress(self, fair_value: FairValueResult) -> str | None:
        if fair_value.fair_value is None:
            return "inactive_no_fair_value"

        if (
            QUOTE_SUPPRESS_SINGLE_LOW_CONFIDENCE
            and fair_value.status == "single_low_confidence_venue"
        ):
            return "inactive_single_low_confidence_venue"

        if (
            fair_value.disagreement_bps is not None
            and fair_value.disagreement_bps >= QUOTE_SUPPRESS_MAX_DISAGREEMENT_BPS
        ):
            return "inactive_excessive_disagreement"

        if (
            QUOTE_SUPPRESS_CROSSED_MARKET
            and fair_value.cross_venue_best_spread is not None
            and fair_value.cross_venue_best_spread <= 0
        ):
            return "inactive_crossed_market"

        if fair_value.market_health == "unhealthy":
            return "inactive_unhealthy_market"

        return None

    def _status_half_spread(self, fair_value: FairValueResult) -> float:
        market_half_spread = 0.0
        if fair_value.cross_venue_best_spread is not None:
            market_half_spread = max(fair_value.cross_venue_best_spread / 2.0, 0.0)

        disagreement_component = 0.0
        if fair_value.disagreement_bps is not None:
            disagreement_component = (
                fair_value.disagreement_bps * QUOTE_DISAGREEMENT_SPREAD_PER_BPS
            )

        half_spread = max(
            self.min_half_spread,
            market_half_spread + disagreement_component,
        )

        if fair_value.status in {"single_venue_only", "single_low_confidence_venue"}:
            half_spread *= QUOTE_DEGRADED_SPREAD_MULTIPLIER

        return half_spread

    def _preferred_size_inputs(self, fair_value: FairValueResult) -> list[VenueQuote]:
        high_confidence_inputs = [
            quote for quote in fair_value.inputs if quote.confidence == "high"
        ]
        if high_confidence_inputs:
            return high_confidence_inputs
        return fair_value.inputs

    def _liquidity_cap(self, fair_value: FairValueResult) -> float:
        size_inputs = self._preferred_size_inputs(fair_value)
        if not size_inputs:
            return self.base_size

        trusted_top_sizes = [
            min(quote.bid_size, quote.ask_size)
            for quote in size_inputs
        ]

        if not trusted_top_sizes:
            return self.base_size

        reference_top_size = min(trusted_top_sizes)
        liquidity_cap = reference_top_size * QUOTE_LIQUIDITY_PARTICIPATION
        return min(self.base_size, liquidity_cap)

    def _health_size_factor(self, fair_value: FairValueResult) -> float:
        if fair_value.market_health == "healthy":
            return QUOTE_SIZE_HEALTHY_MULTIPLIER

        if fair_value.market_health == "degraded":
            return QUOTE_SIZE_DEGRADED_MULTIPLIER

        return QUOTE_SIZE_UNHEALTHY_MULTIPLIER

    def _spread_size_factor(self, fair_value: FairValueResult) -> float:
        size_inputs = self._preferred_size_inputs(fair_value)
        if not size_inputs:
            return 0.0

        tightest_spread_bps = min(quote.spread_bps for quote in size_inputs)

        raw_factor = QUOTE_SIZE_SPREAD_TARGET_BPS / max(
            tightest_spread_bps,
            QUOTE_SIZE_SPREAD_TARGET_BPS,
        )
        return max(QUOTE_SIZE_MIN_SPREAD_FACTOR, min(raw_factor, 1.0))

    def _disagreement_size_factor(self, fair_value: FairValueResult) -> float:
        if fair_value.disagreement_bps is None:
            return 0.0

        disagreement = max(fair_value.disagreement_bps, 0.0)
        scaled = 1.0 - min(disagreement / QUOTE_SIZE_MAX_DISAGREEMENT_BPS, 1.0)
        return max(QUOTE_SIZE_MIN_DISAGREEMENT_FACTOR, min(scaled, 1.0))

    def _side_size_adjustment(self) -> tuple[float, float]:
        utilization = self._inventory_utilization()

        if utilization > 0:
            bid_factor = max(QUOTE_MIN_SIZE_FACTOR, 1.0 - utilization)
            ask_factor = 1.0
            return bid_factor, ask_factor

        if utilization < 0:
            bid_factor = 1.0
            ask_factor = max(QUOTE_MIN_SIZE_FACTOR, 1.0 - abs(utilization))
            return bid_factor, ask_factor

        return 1.0, 1.0

    def _clamp_to_market(
        self,
        fair_value: FairValueResult,
        bid_price: float,
        ask_price: float,
    ) -> tuple[float, float]:
        if fair_value.best_bid is not None:
            bid_price = min(bid_price, fair_value.best_bid - QUOTE_MARKET_EDGE_BUFFER)

        if fair_value.best_ask is not None:
            ask_price = max(ask_price, fair_value.best_ask + QUOTE_MARKET_EDGE_BUFFER)

        return bid_price, ask_price

    def _finalize_side(
        self,
        price: float,
        size: float,
    ) -> tuple[float | None, float | None]:
        rounded_size = round(size, 4)
        if rounded_size < QUOTE_MIN_ABSOLUTE_SIZE:
            return None, None

        return round(price, 2), rounded_size

    def compute(self, fair_value: FairValueResult) -> QuoteRecommendation:
        suppress_status = self._should_suppress(fair_value)
        if suppress_status is not None:
            return QuoteRecommendation(
                reservation_price=None if fair_value.fair_value is None else fair_value.fair_value,
                bid_price=None,
                bid_size=None,
                ask_price=None,
                ask_size=None,
                inventory=self.inventory,
                status=suppress_status,
            )

        reservation_price = fair_value.fair_value - (
            self._inventory_utilization() * self.inventory_skew
        )

        half_spread = self._status_half_spread(fair_value)

        raw_bid_price = reservation_price - half_spread
        raw_ask_price = reservation_price + half_spread
        raw_bid_price, raw_ask_price = self._clamp_to_market(
            fair_value,
            raw_bid_price,
            raw_ask_price,
        )

        if raw_bid_price >= raw_ask_price:
            fallback_half_spread = max(
                half_spread,
                self.min_half_spread,
                (fair_value.cross_venue_best_spread or 0.0) + QUOTE_MARKET_EDGE_BUFFER,
            )
            raw_bid_price = fair_value.fair_value - fallback_half_spread
            raw_ask_price = fair_value.fair_value + fallback_half_spread
            raw_bid_price, raw_ask_price = self._clamp_to_market(
                fair_value,
                raw_bid_price,
                raw_ask_price,
            )

        liquidity_cap = self._liquidity_cap(fair_value)
        health_factor = self._health_size_factor(fair_value)
        spread_factor = self._spread_size_factor(fair_value)
        disagreement_factor = self._disagreement_size_factor(fair_value)

        raw_size = (
            liquidity_cap
            * health_factor
            * spread_factor
            * disagreement_factor
        )

        if fair_value.status in {"single_venue_only", "single_low_confidence_venue"}:
            raw_size *= QUOTE_DEGRADED_SIZE_MULTIPLIER

        bid_size_factor, ask_size_factor = self._side_size_adjustment()

        bid_price, bid_size = self._finalize_side(
            raw_bid_price,
            raw_size * bid_size_factor,
        )
        ask_price, ask_size = self._finalize_side(
            raw_ask_price,
            raw_size * ask_size_factor,
        )

        if fair_value.status == "single_venue_only":
            status = "active_degraded_single_venue"
        elif fair_value.status == "single_low_confidence_venue":
            status = "active_degraded_low_confidence_venue"
        elif fair_value.status == "ok_filtered":
            status = "active_filtered"
        elif fair_value.market_health == "degraded":
            status = "active_degraded"
        else:
            status = "active_two_sided"

        if self.inventory >= self.max_long_inventory:
            bid_price = None
            bid_size = None
            status = "ask_only_inventory_limit"

        if self.inventory <= self.max_short_inventory:
            ask_price = None
            ask_size = None
            status = "bid_only_inventory_limit"

        if bid_price is None and ask_price is None:
            return QuoteRecommendation(
                reservation_price=round(reservation_price, 2),
                bid_price=None,
                bid_size=None,
                ask_price=None,
                ask_size=None,
                inventory=self.inventory,
                status="inactive_size_too_small",
                raw_size=raw_size,
                liquidity_cap=liquidity_cap,
                health_factor=health_factor,
                spread_factor=spread_factor,
                disagreement_factor=disagreement_factor,
                bid_size_factor=bid_size_factor,
                ask_size_factor=ask_size_factor,
                half_spread=half_spread,
            )

        return QuoteRecommendation(
            reservation_price=round(reservation_price, 2),
            bid_price=bid_price,
            bid_size=bid_size,
            ask_price=ask_price,
            ask_size=ask_size,
            inventory=self.inventory,
            status=status,
            raw_size=raw_size,
            liquidity_cap=liquidity_cap,
            health_factor=health_factor,
            spread_factor=spread_factor,
            disagreement_factor=disagreement_factor,
            bid_size_factor=bid_size_factor,
            ask_size_factor=ask_size_factor,
            half_spread=half_spread,
        )
