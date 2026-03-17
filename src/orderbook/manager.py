from dataclasses import dataclass, field

from src.orderbook.book import OrderBook
from src.types import MarketDataEvent


@dataclass
class OrderBookManager:
    # Maintain one local book per venue/source.
    books: dict[str, OrderBook] = field(default_factory=dict)

    def get_book(self, source: str) -> OrderBook:
        if source not in self.books:
            self.books[source] = OrderBook()
        return self.books[source]

    def apply_event(self, event: MarketDataEvent) -> None:
        book = self.get_book(event.source)

        if event.event_type == "snapshot":
            book.apply_snapshot(event.bid_updates, event.ask_updates)
        elif event.event_type == "update":
            book.apply_update(event.bid_updates, event.ask_updates)
        else:
            raise ValueError(f"unsupported event_type: {event.event_type}")

    def top_of_book(self, source: str) -> dict:
        book = self.get_book(source)
        return {
            "source": source,
            "best_bid": book.best_bid(),
            "best_ask": book.best_ask(),
        }
