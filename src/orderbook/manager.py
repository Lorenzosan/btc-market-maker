from dataclasses import dataclass, field

from src.orderbook.book import OrderBook
from src.types import MarketDataEvent


@dataclass
class BookState:
    # Local book for a single venue.
    book: OrderBook = field(default_factory=OrderBook)

    # Whether we have already received a snapshot for this venue.
    initialized: bool = False

    # Whether the current local book looks internally valid.
    # In this implementation, that mainly means "not crossed".
    valid: bool = False

    # Last known sequence information when available.
    # This is meaningful for Binance, not for Coinbase level2_batch here.
    last_sequence: int | None = None

    # Human-readable state for logging and debugging.
    status: str = "waiting_for_snapshot"


@dataclass
class OrderBookManager:
    # One independent local state per source venue.
    states: dict[str, BookState] = field(default_factory=dict)

    def get_state(self, source: str) -> BookState:
        # Lazily create state the first time we see a venue.
        if source not in self.states:
            self.states[source] = BookState()
        return self.states[source]

    def apply_event(self, event: MarketDataEvent) -> None:
        # Apply a normalized market-data event to the corresponding venue book.
        state = self.get_state(event.source)

        if event.event_type == "snapshot":
            # Snapshot replaces the full local book state for that venue.
            state.book.apply_snapshot(event.bid_updates, event.ask_updates)
            state.initialized = True
            state.valid = not state.book.is_crossed()
            state.last_sequence = event.sequence
            state.status = "ok" if state.valid else "crossed_after_snapshot"
            return

        if event.event_type != "update":
            raise ValueError(f"unsupported event_type: {event.event_type}")

        # Never apply updates before a snapshot because there is no base state.
        if not state.initialized:
            state.valid = False
            state.status = "update_before_snapshot"
            return

        if event.source == "binance":
            # Binance sequencing has already been validated in the connector.
            # The manager therefore only applies the already-sanitized update.
            state.book.apply_update(event.bid_updates, event.ask_updates)
            state.valid = not state.book.is_crossed()
            state.last_sequence = event.sequence
            state.status = "ok" if state.valid else "crossed_after_update"
            return

        if event.source == "coinbase":
            # Coinbase public level2_batch does not expose the same explicit
            # numeric continuity mechanism used in the Binance connector here.
            # We still maintain the book from snapshot plus updates.
            state.book.apply_update(event.bid_updates, event.ask_updates)
            state.valid = not state.book.is_crossed()
            state.status = "ok_no_sequence_validation" if state.valid else "crossed_after_update"
            return

        raise ValueError(f"unsupported source: {event.source}")

    def top_of_book(self, source: str) -> dict:
        # Return a compact summary used by the output layer.
        state = self.get_state(source)
        
        best_bid = state.book.best_bid()
        best_ask = state.book.best_ask()
        
        mid = None
        spread = None

        if best_bid is not None and best_ask is not None:
            mid = round((best_bid[0] + best_ask[0]) / 2.0, 2)
            spread = round(best_ask[0] - best_bid[0], 2)
            
        return {
            "source": source,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid": mid,
            "spread": spread,
            "initialized": state.initialized,
            "valid": state.valid,
            "last_sequence": state.last_sequence,
            "status": state.status,
        }
