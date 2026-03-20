from dataclasses import dataclass

from src.orderbook.manager import OrderBookManager


@dataclass
class VenueQuote:
    # Compact per-venue pricing view used by the fair-value engine.
    source: str
    bid: float
    ask: float
    mid: float
    spread: float
    weight: float


@dataclass
class FairValueResult:
    # Final fair-value output plus diagnostics.
    fair_value: float | None
    inputs: list[VenueQuote]
    status: str


class FairValueEngine:
    def __init__(self, max_spread: float = 1.0) -> None:
        # Venues wider than this are excluded from pricing.
        self.max_spread = max_spread

    def _extract_usable_quote(
        self,
        manager: OrderBookManager,
        source: str,
    ) -> VenueQuote | None:
        # Pull one venue out of the manager and decide whether it is usable.
        state = manager.get_state(source)

        if not state.initialized:
            return None
        if not state.valid:
            return None
        if state.is_stale:
            return None
        
        best_bid = state.book.best_bid()
        best_ask = state.book.best_ask()

        if best_bid is None or best_ask is None:
            return None

        bid_price = best_bid[0]
        ask_price = best_ask[0]
        spread = ask_price - bid_price

        if spread <= 0:
            return None

        # Exclude venues with excessive spread, as they likely indicate
        # poor book quality or unreliable pricing for fair-value purposes.
        if spread > self.max_spread:
            return None

        mid = (bid_price + ask_price) / 2.0

        # Inverse-spread weighting:
        # tighter books get more influence on the fair value.
        weight = 1.0 / spread

        return VenueQuote(
            source=source,
            bid=bid_price,
            ask=ask_price,
            mid=mid,
            spread=spread,
            weight=weight,
        )

    def compute(self, manager: OrderBookManager) -> FairValueResult:
        # Collect usable venues from the current manager state.
        quotes: list[VenueQuote] = []

        for source in sorted(manager.states.keys()):
            quote = self._extract_usable_quote(manager, source)
            if quote is not None:
                quotes.append(quote)

        if not quotes:
            return FairValueResult(
                fair_value=None,
                inputs=[],
                status="no_usable_venues",
            )

        total_weight = sum(q.weight for q in quotes)
        if total_weight <= 0:
            return FairValueResult(
                fair_value=None,
                inputs=quotes,
                status="invalid_weights",
            )

        # Note: BTC-USD and BTCUSDT are treated as near-equivalent here.
        # USDT/USD basis is ignored for simplicity in this take-home version.
        fair_value = sum(q.mid * q.weight for q in quotes) / total_weight

        status = "ok" if len(quotes) >= 2 else "single_venue_only"

        return FairValueResult(
            fair_value=round(fair_value, 2),
            inputs=quotes,
            status=status,
        )
