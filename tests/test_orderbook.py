from src.orderbook.book import OrderBook


def test_snapshot_sets_best_bid_and_best_ask():
    book = OrderBook()

    book.apply_snapshot(
        bid_updates=[(100.0, 1.0), (99.0, 2.0)],
        ask_updates=[(101.0, 1.5), (102.0, 3.0)],
    )

    assert book.best_bid() == (100.0, 1.0)
    assert book.best_ask() == (101.0, 1.5)


def test_update_modifies_existing_level():
    book = OrderBook()

    book.apply_snapshot(
        bid_updates=[(100.0, 1.0)],
        ask_updates=[(101.0, 1.5)],
    )

    book.apply_update(
        bid_updates=[(100.0, 2.5)],
        ask_updates=[],
    )

    assert book.best_bid() == (100.0, 2.5)


def test_update_removes_level_when_size_is_zero():
    book = OrderBook()

    book.apply_snapshot(
        bid_updates=[(100.0, 1.0), (99.0, 2.0)],
        ask_updates=[(101.0, 1.5)],
    )

    book.apply_update(
        bid_updates=[(100.0, 0.0)],
        ask_updates=[],
    )

    assert book.best_bid() == (99.0, 2.0)


def test_crossed_book_is_detected():
    book = OrderBook()

    book.apply_snapshot(
        bid_updates=[(101.0, 1.0)],
        ask_updates=[(100.0, 1.0)],
    )

    assert book.is_crossed() is True
