from dataclasses import dataclass, field

from src.orderbook.book import OrderBook
from src.types import MarketDataEvent

import time

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

    # Monotonic timestamp of the last successfully APPLIED update or snapshot.
    # Must only be updated after the book has been modified.
    last_update_monotonic: float | None = None

    # Wall-clock timestamp (string) of the last received event.
    # Used only for logging/output, not for logic.
    last_received_ts: str | None = None

    # Whether the venue is currently considered stale.
    # True until first successful update is applied.
    is_stale: bool = True

    # Human-readable state for logging and debugging.
    status: str = "waiting_for_snapshot"

    def age_ms(self, now_monotonic: float) -> float | None:
        if self.last_update_monotonic is None:
            return None
        return (now_monotonic - self.last_update_monotonic) * 1000.0

@dataclass
class OrderBookManager:
    # One independent local state per source venue.
    states: dict[str, BookState] = field(default_factory=dict)

    def get_state(self, source: str) -> BookState:
        # Lazily create state the first time we see a venue.
        if source not in self.states:
            self.states[source] = BookState()
        return self.states[source]

    def _mark_update_applied(self, state: BookState, event: MarketDataEvent) -> None:
        # Record freshness only after a snapshot or update has been applied.
        state.last_update_monotonic = time.monotonic()
        state.last_received_ts = event.received_ts
        state.is_stale = False

    def refresh_staleness(self, stale_after_s: float, now_monotonic: float | None = None) -> None:
        # Recompute stale status for all venues from the monotonic clock.
        if now_monotonic is None:
            now_monotonic = time.monotonic()

        for state in self.states.values():
            if state.last_update_monotonic is None:
                state.is_stale = True
                continue

            state.is_stale = (now_monotonic - state.last_update_monotonic) > stale_after_s

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
            self._mark_update_applied(state, event)
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
            self._mark_update_applied(state, event)
            return

        if event.source == "coinbase":
            # Coinbase public level2_batch does not expose the same explicit
            # numeric continuity mechanism used in the Binance connector here.
            # We still maintain the book from snapshot plus updates.
            state.book.apply_update(event.bid_updates, event.ask_updates)
            state.valid = not state.book.is_crossed()
            state.status = "ok_no_sequence_validation" if state.valid else "crossed_after_update"
            self._mark_update_applied(state, event)
            return

        raise ValueError(f"unsupported source: {event.source}")

    def top_of_book(self, source: str, now_monotonic: float | None = None) -> dict:
        # Return a compact summary used by the output layer.
        state = self.get_state(source)

        if now_monotonic is None:
            now_monotonic = time.monotonic()

        best_bid = state.book.best_bid()
        best_ask = state.book.best_ask()

        mid = None
        spread = None

        if best_bid is not None and best_ask is not None:
            mid = round((best_bid[0] + best_ask[0]) / 2.0, 2)
            spread = round(best_ask[0] - best_bid[0], 2)

        age_ms = state.age_ms(now_monotonic)
        if age_ms is not None:
            age_ms = round(age_ms, 1)

        return {
            "source": source,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid": mid,
            "spread": spread,
            "initialized": state.initialized,
            "valid": state.valid,
            "last_sequence": state.last_sequence,
            "last_received_ts": state.last_received_ts,
            "age_ms": age_ms,
            "is_stale": state.is_stale,
            "status": state.status,
        }
