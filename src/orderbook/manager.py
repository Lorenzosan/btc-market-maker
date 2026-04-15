import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.config import COINBASE_QUARANTINE_ON_CROSSED_BOOK
from src.orderbook.factory import create_order_book
from src.types import MarketDataEvent

@dataclass
class BookState:
    book: object
    initialized: bool = False
    valid: bool = False
    last_sequence: int | None = None
    last_update_monotonic: float | None = None
    last_received_ts: str | None = None
    last_exchange_ts: str | float | int | None = None
    is_stale: bool = True
    needs_resync: bool = False
    last_snapshot_monotonic: float | None = None
    last_resync_monotonic: float | None = None
    status: str = "waiting_for_snapshot"

    def age_ms(self, now_monotonic: float) -> float | None:
        if self.last_update_monotonic is None:
            return None
        return (now_monotonic - self.last_update_monotonic) * 1000.0

    def seconds_since_resync(self, now_monotonic: float) -> float | None:
        if self.last_resync_monotonic is None:
            return None
        return now_monotonic - self.last_resync_monotonic

    
@dataclass
class OrderBookManager:
    states: dict[str, BookState] = field(default_factory=dict)
    backend: str = "python"

    def get_state(self, source: str) -> BookState:
        if source not in self.states:
            self.states[source] = BookState(
                book=create_order_book(self.backend)
            )
        return self.states[source]
    
    def _mark_update_applied(self, state: BookState, event: MarketDataEvent) -> None:
        # Record freshness only after a snapshot or update has been applied.
        state.last_update_monotonic = time.monotonic()
        state.last_received_ts = event.received_ts
        state.last_exchange_ts = event.exchange_ts
        state.is_stale = False

    def _parse_exchange_ts(self, value: str | float | int | None) -> datetime | None:
        # Parse either ISO strings or numeric unix timestamps.
        if value is None:
            return None

        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)

        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        
        if isinstance(value, str):
            normalized = value.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized).astimezone(timezone.utc)
        
        # Unknown timestamp format. Ignore monotonicity validation instead of crashing.
        return None

    def _is_exchange_ts_backwards(self, state: BookState, event: MarketDataEvent) -> bool:
        # Reject obviously older exchange timestamps for Coinbase updates.
        current_ts = self._parse_exchange_ts(event.exchange_ts)
        previous_ts = self._parse_exchange_ts(state.last_exchange_ts)

        if current_ts is None or previous_ts is None:
            return False

        return current_ts < previous_ts

    def _apply_snapshot(self, state: BookState, event: MarketDataEvent) -> None:
        # Snapshot replaces the full local book state for that venue.
        was_waiting_for_resync = state.needs_resync

        state.book.apply_snapshot(event.bid_updates, event.ask_updates)
        state.initialized = True
        state.valid = not state.book.is_crossed()
        state.last_sequence = event.sequence
        state.needs_resync = False
        state.status = "ok" if state.valid else "crossed_after_snapshot"
        self._mark_update_applied(state, event)

        now_monotonic = state.last_update_monotonic
        state.last_snapshot_monotonic = now_monotonic

        if was_waiting_for_resync and state.valid:
            state.last_resync_monotonic = now_monotonic

        if not state.valid:
            state.needs_resync = True

    def refresh_staleness(
        self,
        stale_after_s: float,
        now_monotonic: float | None = None,
    ) -> None:
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
            self._apply_snapshot(state, event)
            return

        if event.event_type != "update":
            raise ValueError(f"unsupported event_type: {event.event_type}")

        if not state.initialized:
            state.valid = False
            state.status = "update_before_snapshot"
            return

        if event.source == "binance":
            state.book.apply_update(event.bid_updates, event.ask_updates)
            state.valid = not state.book.is_crossed()
            state.last_sequence = event.sequence
            state.status = "ok" if state.valid else "crossed_after_update"
            self._mark_update_applied(state, event)

            if not state.valid:
                state.needs_resync = True

            return

        if event.source == "coinbase":
            if state.needs_resync:
                state.status = "waiting_for_resync_snapshot"
                return

            if self._is_exchange_ts_backwards(state, event):
                state.valid = False
                state.needs_resync = True
                state.status = "coinbase_non_monotonic_exchange_ts"
                return

            state.book.apply_update(event.bid_updates, event.ask_updates)
            state.valid = not state.book.is_crossed()
            state.last_sequence = event.sequence
            state.status = "ok_best_effort"

            if not state.valid and COINBASE_QUARANTINE_ON_CROSSED_BOOK:
                state.needs_resync = True
                state.status = "coinbase_crossed_waiting_for_resync"

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

        seconds_since_resync = state.seconds_since_resync(now_monotonic)
        if seconds_since_resync is not None:
            seconds_since_resync = round(seconds_since_resync, 3)

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
            "last_exchange_ts": state.last_exchange_ts,
            "age_ms": age_ms,
            "is_stale": state.is_stale,
            "needs_resync": state.needs_resync,
            "seconds_since_resync": seconds_since_resync,
            "status": state.status,
        }
