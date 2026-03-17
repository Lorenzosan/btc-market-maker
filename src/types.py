from dataclasses import dataclass
from typing import Literal, Optional

PriceLevel = tuple[float, float]  # (price, size)

# Normalized representation of a single market data message.
# For update events, bid_updates and ask_updates contain only
# changed price levels (deltas), not the full order book state.
@dataclass
class MarketDataEvent:
    source: Literal["binance", "coinbase"]
    symbol: str
    channel: str
    event_type: Literal["snapshot", "update"]
    exchange_ts: Optional[str]
    received_ts: str
    sequence: Optional[int]
    sequence_start: Optional[int] = None
    sequence_end: Optional[int] = None
    bid_updates: list[PriceLevel] = None
    ask_updates: list[PriceLevel] = None
    raw: Optional[dict] = None
