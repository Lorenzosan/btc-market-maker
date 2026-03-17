from dataclasses import dataclass, field

from src.types import PriceLevel


@dataclass
class OrderBook:
    # Local in-memory order book keyed by price.
    # Values are sizes at each price level.
    bids: dict[float, float] = field(default_factory=dict)
    asks: dict[float, float] = field(default_factory=dict)

    def apply_snapshot(self, bid_updates: list[PriceLevel], ask_updates: list[PriceLevel]) -> None:
        # Snapshot replaces the full local state for each side.
        self.bids = {price: size for price, size in bid_updates if size > 0}
        self.asks = {price: size for price, size in ask_updates if size > 0}

    def apply_update(self, bid_updates: list[PriceLevel], ask_updates: list[PriceLevel]) -> None:
        # Updates are price-level deltas:
        # size == 0 means remove the level, otherwise insert/update it.
        for price, size in bid_updates:
            if size == 0:
                self.bids.pop(price, None)
            else:
                self.bids[price] = size

        for price, size in ask_updates:
            if size == 0:
                self.asks.pop(price, None)
            else:
                self.asks[price] = size

    def best_bid(self) -> PriceLevel | None:
        if not self.bids:
            return None
        price = max(self.bids)
        return price, self.bids[price]

    def best_ask(self) -> PriceLevel | None:
        if not self.asks:
            return None
        price = min(self.asks)
        return price, self.asks[price]
