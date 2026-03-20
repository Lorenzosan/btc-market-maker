from dataclasses import dataclass

from src.config import (
    INITIAL_INVENTORY,
    MAX_LONG_INVENTORY,
    MAX_SHORT_INVENTORY,
    QUOTE_BASE_SIZE,
    QUOTE_DEGRADED_SIZE_MULTIPLIER,
    QUOTE_DEGRADED_SPREAD_MULTIPLIER,
    QUOTE_HALF_SPREAD,
    QUOTE_INVENTORY_SKEW,
    QUOTE_LIQUIDITY_PARTICIPATION,
    QUOTE_MIN_SIZE_FACTOR,
)
from src.fair_value.fair_value import FairValueResult


@dataclass
class QuoteRecommendation:
    # Reservation price after inventory adjustment.
    reservation_price: float | None

    # Recommended prices and sizes.
    bid_price: float | None
    bid_size: float | None
    ask_price: float | None
    ask_size: float | None

    # Current inventory state used for skewing.
    inventory: float

    # Human-readable quote state.
    status: str


class QuoteEngine:
    def __init__(
        self,
        base_size: float = QUOTE_BASE_SIZE,
        half_spread: float = QUOTE_HALF_SPREAD,
        inventory_skew: float = QUOTE_INVENTORY_SKEW,
        inventory: float = INITIAL_INVENTORY,
        max_long_inventory: float = MAX_LONG_INVENTORY,
        max_short_inventory: float = MAX_SHORT_INVENTORY,
    ) -> None:
        self.base_size = base_size
        self.half_spread = half_spread
        self.inventory_skew = inventory_skew
        self.inventory = inventory
        self.max_long_inventory = max_long_inventory
        self.max_short_inventory = max_short_inventory

    def _status_half_spread(self, fair_value: FairValueResult) -> float:
        # Widen quotes when fair value is based on only one usable venue.
        if fair_value.status == "single_venue_only":
            return self.half_spread * QUOTE_DEGRADED_SPREAD_MULTIPLIER
        return self.half_spread

    def _inventory_size_factor(self) -> float:
        # Reduce quote size as inventory approaches hard limits.
        if self.inventory > 0 and self.max_long_inventory > 0:
            utilization = self.inventory / self.max_long_inventory
        elif self.inventory < 0 and self.max_short_inventory < 0:
            utilization = abs(self.inventory / self.max_short_inventory)
        else:
            utilization = 0.0

        utilization = min(max(utilization, 0.0), 1.0)
        return max(QUOTE_MIN_SIZE_FACTOR, 1.0 - utilization)

    def _health_size_factor(self, fair_value: FairValueResult) -> float:
        # Reduce quote size when fair value is supported by only one venue.
        if fair_value.status == "single_venue_only":
            return QUOTE_DEGRADED_SIZE_MULTIPLIER
        return 1.0

    def _liquidity_capped_size(self, fair_value: FairValueResult) -> float:
        # Use a conservative fraction of visible top-of-book liquidity as a cap.
        if not fair_value.inputs:
            return self.base_size

        visible_sizes = [
            min(q.bid_size, q.ask_size)
            for q in fair_value.inputs
            if q.bid_size > 0 and q.ask_size > 0
        ]

        if not visible_sizes:
            return self.base_size

        liquidity_cap = min(visible_sizes) * QUOTE_LIQUIDITY_PARTICIPATION
        return min(self.base_size, liquidity_cap)

    def compute(self, fair_value: FairValueResult) -> QuoteRecommendation:
        # If no fair value is available, quoting must be disabled.
        if fair_value.fair_value is None:
            return QuoteRecommendation(
                reservation_price=None,
                bid_price=None,
                bid_size=None,
                ask_price=None,
                ask_size=None,
                inventory=self.inventory,
                status="inactive_no_fair_value",
            )

        # Reservation price shifts against current inventory.
        reservation_price = fair_value.fair_value - (self.inventory * self.inventory_skew)

        half_spread = self._status_half_spread(fair_value)

        bid_price = round(reservation_price - half_spread, 2)
        ask_price = round(reservation_price + half_spread, 2)

        raw_size = (
            self._liquidity_capped_size(fair_value)
            * self._inventory_size_factor()
            * self._health_size_factor(fair_value)
        )
        size = round(raw_size, 4)

        bid_size = size
        ask_size = size

        # Distinguish normal quoting from degraded single-venue quoting.
        if fair_value.status == "single_venue_only":
            status = "active_degraded_single_venue"
        else:
            status = "active_two_sided"

        # If inventory is too long, stop buying and only quote the ask side.
        if self.inventory >= self.max_long_inventory:
            bid_price = None
            bid_size = None
            status = "ask_only_inventory_limit"

        # If inventory is too short, stop selling and only quote the bid side.
        if self.inventory <= self.max_short_inventory:
            ask_price = None
            ask_size = None
            status = "bid_only_inventory_limit"

        return QuoteRecommendation(
            reservation_price=round(reservation_price, 2),
            bid_price=bid_price,
            bid_size=bid_size,
            ask_price=ask_price,
            ask_size=ask_size,
            inventory=self.inventory,
            status=status,
        )
