from src.orderbook.manager import OrderBookManager
from src.types import MarketDataEvent


def make_event(
    *,
    source: str,
    symbol: str,
    channel: str,
    event_type: str,
    bid_updates,
    ask_updates,
    sequence,
    exchange_ts,
    received_ts: str,
):
    return MarketDataEvent(
        source=source,
        symbol=symbol,
        channel=channel,
        event_type=event_type,
        bid_updates=bid_updates,
        ask_updates=ask_updates,
        sequence=sequence,
        exchange_ts=exchange_ts,
        received_ts=received_ts,
    )


def assert_same_top(py_top: dict, cpp_top: dict) -> None:
    assert py_top["best_bid"] == cpp_top["best_bid"]
    assert py_top["best_ask"] == cpp_top["best_ask"]
    assert py_top["mid"] == cpp_top["mid"]
    assert py_top["spread"] == cpp_top["spread"]
    assert py_top["initialized"] == cpp_top["initialized"]
    assert py_top["valid"] == cpp_top["valid"]
    assert py_top["last_sequence"] == cpp_top["last_sequence"]
    assert py_top["needs_resync"] == cpp_top["needs_resync"]
    assert py_top["status"] == cpp_top["status"]


def test_binance_python_and_cpp_backends_match():
    manager_py = OrderBookManager(backend="python")
    manager_cpp = OrderBookManager(backend="cpp")

    events = [
        make_event(
            source="binance",
            symbol="BTCUSDT",
            channel="depth",
            event_type="snapshot",
            bid_updates=[(100.0, 1.0), (99.0, 2.0)],
            ask_updates=[(101.0, 1.5), (102.0, 3.0)],
            sequence=10,
            exchange_ts=0.0,
            received_ts="2026-03-20T12:00:00Z",
        ),
        make_event(
            source="binance",
            symbol="BTCUSDT",
            channel="depth",
            event_type="update",
            bid_updates=[(100.0, 1.2), (98.0, 4.0)],
            ask_updates=[(101.0, 0.0), (100.5, 2.0)],
            sequence=11,
            exchange_ts=1.0,
            received_ts="2026-03-20T12:00:01Z",
        ),
        make_event(
            source="binance",
            symbol="BTCUSDT",
            channel="depth",
            event_type="update",
            bid_updates=[(99.0, 0.0)],
            ask_updates=[(102.0, 1.0)],
            sequence=12,
            exchange_ts=2.0,
            received_ts="2026-03-20T12:00:02Z",
        ),
    ]

    for event in events:
        manager_py.apply_event(event)
        manager_cpp.apply_event(event)

        py_top = manager_py.top_of_book(event.source, now_monotonic=0.0)
        cpp_top = manager_cpp.top_of_book(event.source, now_monotonic=0.0)

        assert_same_top(py_top, cpp_top)


def test_coinbase_python_and_cpp_backends_match():
    manager_py = OrderBookManager(backend="python")
    manager_cpp = OrderBookManager(backend="cpp")

    events = [
        make_event(
            source="coinbase",
            symbol="BTC-USD",
            channel="level2",
            event_type="snapshot",
            bid_updates=[(100.0, 1.0), (99.0, 2.0)],
            ask_updates=[(101.0, 1.5), (102.0, 3.0)],
            sequence=None,
            exchange_ts="2026-03-20T12:00:00Z",
            received_ts="2026-03-20T12:00:00Z",
        ),
        make_event(
            source="coinbase",
            symbol="BTC-USD",
            channel="level2",
            event_type="update",
            bid_updates=[(100.0, 1.2)],
            ask_updates=[(101.0, 0.0), (100.5, 2.0)],
            sequence=None,
            exchange_ts="2026-03-20T12:00:01Z",
            received_ts="2026-03-20T12:00:01Z",
        ),
        make_event(
            source="coinbase",
            symbol="BTC-USD",
            channel="level2",
            event_type="update",
            bid_updates=[(99.0, 0.0)],
            ask_updates=[(102.0, 1.0)],
            sequence=None,
            exchange_ts="2026-03-20T12:00:02Z",
            received_ts="2026-03-20T12:00:02Z",
        ),
    ]

    for event in events:
        manager_py.apply_event(event)
        manager_cpp.apply_event(event)

        py_top = manager_py.top_of_book(event.source, now_monotonic=0.0)
        cpp_top = manager_cpp.top_of_book(event.source, now_monotonic=0.0)

        assert_same_top(py_top, cpp_top)
