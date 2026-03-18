from dataclasses import dataclass

from src.config import (
    INITIAL_INVENTORY,
    MAX_LONG_INVENTORY,
    MAX_SHORT_INVENTORY,
    QUOTE_BASE_SIZE,
    QUOTE_HALF_SPREAD,
    QUOTE_INVENTORY_SKEW,
)
from src.quoting.fair_value import FairValueResult


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

        bid_price = round(reservation_price - self.half_spread, 2)
        ask_price = round(reservation_price + self.half_spread, 2)

        bid_size = self.base_size
        ask_size = self.base_size
        status = "active"

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
