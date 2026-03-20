from src.orderbook.manager import OrderBookManager
from src.types import MarketDataEvent


def test_update_before_snapshot_is_rejected():
    manager = OrderBookManager()

    event = MarketDataEvent(
        source="binance",
        symbol="BTCUSDT",
        channel="depth",
        event_type="update",
        bid_updates=[(100.0, 1.0)],
        ask_updates=[(101.0, 1.0)],
        sequence=10,
        exchange_ts=0.0,
        received_ts="2026-03-20T12:00:00Z",
    )
    manager.apply_event(event)

    state = manager.get_state("binance")

    assert state.initialized is False
    assert state.valid is False
    assert state.last_update_monotonic is None
    assert state.last_received_ts is None
    assert state.is_stale is True
    assert state.status == "update_before_snapshot"


def test_snapshot_initializes_book_and_marks_venue_fresh():
    manager = OrderBookManager()

    event = MarketDataEvent(
        source="binance",
        symbol="BTCUSDT",
        channel="depth",
        event_type="snapshot",
        bid_updates=[(100.0, 1.0)],
        ask_updates=[(101.0, 1.0)],
        sequence=10,
        exchange_ts=0.0,
        received_ts="2026-03-20T12:00:00Z",
    )
    manager.apply_event(event)

    state = manager.get_state("binance")

    assert state.initialized is True
    assert state.valid is True
    assert state.last_sequence == 10
    assert state.last_update_monotonic is not None
    assert state.last_received_ts == "2026-03-20T12:00:00Z"
    assert state.is_stale is False
    assert state.status == "ok"


def test_binance_update_tracks_sequence_and_refreshes_freshness():
    manager = OrderBookManager()

    snapshot = MarketDataEvent(
        source="binance",
        symbol="BTCUSDT",
        channel="depth",
        event_type="snapshot",
        bid_updates=[(100.0, 1.0)],
        ask_updates=[(101.0, 1.0)],
        sequence=10,
        exchange_ts=0.0,
        received_ts="2026-03-20T12:00:00Z",
    )
    manager.apply_event(snapshot)

    first_update_ts = manager.get_state("binance").last_update_monotonic

    update = MarketDataEvent(
        source="binance",
        symbol="BTCUSDT",
        channel="depth",
        event_type="update",
        bid_updates=[(100.5, 1.2)],
        ask_updates=[],
        sequence=11,
        exchange_ts=1.0,
        received_ts="2026-03-20T12:00:01Z",
    )
    manager.apply_event(update)

    state = manager.get_state("binance")

    assert state.valid is True
    assert state.last_sequence == 11
    assert state.last_update_monotonic is not None
    assert first_update_ts is not None
    assert state.last_update_monotonic >= first_update_ts
    assert state.last_received_ts == "2026-03-20T12:00:01Z"
    assert state.is_stale is False
    assert state.status == "ok"
    assert state.book.best_bid() == (100.5, 1.2)


def test_coinbase_update_has_no_sequence_validation_status_and_refreshes_freshness():
    manager = OrderBookManager()

    snapshot = MarketDataEvent(
        source="coinbase",
        symbol="BTC-USD",
        channel="level2",
        event_type="snapshot",
        bid_updates=[(100.0, 1.0)],
        ask_updates=[(101.0, 1.0)],
        sequence=None,
        exchange_ts=0.0,
        received_ts="2026-03-20T12:00:00Z",
    )
    manager.apply_event(snapshot)

    update = MarketDataEvent(
        source="coinbase",
        symbol="BTC-USD",
        channel="level2",
        event_type="update",
        bid_updates=[(100.5, 1.2)],
        ask_updates=[],
        sequence=None,
        exchange_ts=1.0,
        received_ts="2026-03-20T12:00:01Z",
    )
    manager.apply_event(update)

    state = manager.get_state("coinbase")

    assert state.initialized is True
    assert state.valid is True
    assert state.last_update_monotonic is not None
    assert state.last_received_ts == "2026-03-20T12:00:01Z"
    assert state.is_stale is False
    assert state.status == "ok_no_sequence_validation"
    assert state.book.best_bid() == (100.5, 1.2)


def test_refresh_staleness_marks_venue_stale_after_timeout():
    manager = OrderBookManager()

    snapshot = MarketDataEvent(
        source="binance",
        symbol="BTCUSDT",
        channel="depth",
        event_type="snapshot",
        bid_updates=[(100.0, 1.0)],
        ask_updates=[(101.0, 1.0)],
        sequence=10,
        exchange_ts=0.0,
        received_ts="2026-03-20T12:00:00Z",
    )
    manager.apply_event(snapshot)

    state = manager.get_state("binance")
    assert state.last_update_monotonic is not None
    assert state.is_stale is False

    manager.refresh_staleness(
        stale_after_s=1.5,
        now_monotonic=state.last_update_monotonic + 2.0,
    )

    assert state.is_stale is True


def test_top_of_book_exposes_freshness_fields():
    manager = OrderBookManager()

    snapshot = MarketDataEvent(
        source="binance",
        symbol="BTCUSDT",
        channel="depth",
        event_type="snapshot",
        bid_updates=[(100.0, 1.0)],
        ask_updates=[(101.0, 2.0)],
        sequence=10,
        exchange_ts=0.0,
        received_ts="2026-03-20T12:00:00Z",
    )
    manager.apply_event(snapshot)

    state = manager.get_state("binance")
    assert state.last_update_monotonic is not None

    top = manager.top_of_book(
        "binance",
        now_monotonic=state.last_update_monotonic + 0.25,
    )

    assert top["source"] == "binance"
    assert top["best_bid"] == (100.0, 1.0)
    assert top["best_ask"] == (101.0, 2.0)
    assert top["mid"] == 100.5
    assert top["spread"] == 1.0
    assert top["last_received_ts"] == "2026-03-20T12:00:00Z"
    assert top["age_ms"] == 250.0
    assert top["is_stale"] is False
