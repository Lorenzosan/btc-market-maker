from dataclasses import dataclass, field
from typing import Literal, Optional

# Normalized price level represented as (price, size).
PriceLevel = tuple[float, float]


@dataclass
class MarketDataEvent:
    # Source venue of the event.
    source: Literal["binance", "coinbase"]

    # Instrument symbol as provided or normalized by the venue connector.
    symbol: str

    # Venue channel name, useful for debugging and design notes.
    channel: str

    # Snapshot replaces the full local book, update applies deltas.
    event_type: Literal["snapshot", "update"]

    # Exchange-provided timestamp when available.
    exchange_ts: Optional[str]

    # Local receive timestamp.
    received_ts: str

    # Generic sequence field when the venue provides one and it is worth exposing.
    # For Binance we use this as the last validated update id after the connector
    # has already performed snapshot bridging and continuity checks.
    sequence: Optional[int]

    # Changed bid levels or full bid side for snapshots.
    bid_updates: list[PriceLevel] = field(default_factory=list)

    # Changed ask levels or full ask side for snapshots.
    ask_updates: list[PriceLevel] = field(default_factory=list)

    # Raw venue payload kept for debugging.
    raw: Optional[dict] = None
