from dataclasses import dataclass
from typing import Literal, Optional

PriceLevel = tuple[float, float]

#
# This class represents one normalized market event
#
# For update events, bid_updates and ask_updates are
# changed price levels, not the full state of the
# order book.
#
@dataclass
class MarketDataEvent:
    source: Literal["binance", "coinbase"]
    symbol: str
    channel: str
    event_type: Literal["snapshot", "update"]
    exchange_ts: Optional[str]
    received_ts: str
    sequence: Optional[int]
    bid_updates: list[PriceLevel]
    ask_updates: list[PriceLevel]
    raw: dict
