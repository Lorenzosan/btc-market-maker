from src.orderbook.manager import OrderBookManager
from src.quoting.fair_value import FairValueEngine
from src.types import MarketDataEvent


def test_no_usable_venues_returns_none():
    manager = OrderBookManager()
    engine = FairValueEngine(max_spread=1.0)

    result = engine.compute(manager)

    assert result.fair_value is None
    assert result.inputs == []
    assert result.status == "no_usable_venues"


def test_single_venue_fair_value_equals_mid():
    manager = OrderBookManager()
    engine = FairValueEngine(max_spread=1.0)

    snapshot = MarketDataEvent(
        source="binance",
        symbol="BTCUSDT",
        channel="depth",
        event_type="snapshot",
        bid_updates=[(100.0, 1.0)],
        ask_updates=[(101.0, 1.0)],
        sequence=10,
        exchange_ts=0.0,
        received_ts=0.0,
    )
    manager.apply_event(snapshot)

    result = engine.compute(manager)

    assert result.fair_value == 100.5
    assert result.status == "ok"
    assert len(result.inputs) == 1


def test_inverse_spread_weighting():
    manager = OrderBookManager()
    engine = FairValueEngine(max_spread=2.0)

    manager.apply_event(
        MarketDataEvent(
            source="binance",
            symbol="BTCUSDT",
            channel="depth",
            event_type="snapshot",
            bid_updates=[(100.0, 1.0)],
            ask_updates=[(101.0, 1.0)],
            sequence=10,
            exchange_ts=0.0,
            received_ts=0.0,
        )
    )

    manager.apply_event(
        MarketDataEvent(
            source="coinbase",
            symbol="BTC-USD",
            channel="level2",
            event_type="snapshot",
            bid_updates=[(100.0, 1.0)],
            ask_updates=[(100.5, 1.0)],
            sequence=None,
            exchange_ts=0.0,
            received_ts=0.0,
        )
    )

    result = engine.compute(manager)

    expected = round(((100.5 * 1.0) + (100.25 * 2.0)) / 3.0, 2)
    assert result.fair_value == expected
    assert result.status == "ok"
    assert len(result.inputs) == 2


def test_wide_spread_venue_is_excluded():
    manager = OrderBookManager()
    engine = FairValueEngine(max_spread=1.0)

    manager.apply_event(
        MarketDataEvent(
            source="binance",
            symbol="BTCUSDT",
            channel="depth",
            event_type="snapshot",
            bid_updates=[(100.0, 1.0)],
            ask_updates=[(101.0, 1.0)],
            sequence=10,
            exchange_ts=0.0,
            received_ts=0.0,
        )
    )

    manager.apply_event(
        MarketDataEvent(
            source="coinbase",
            symbol="BTC-USD",
            channel="level2",
            event_type="snapshot",
            bid_updates=[(90.0, 1.0)],
            ask_updates=[(110.0, 1.0)],
            sequence=None,
            exchange_ts=0.0,
            received_ts=0.0,
        )
    )

    result = engine.compute(manager)

    assert result.fair_value == 100.5
    assert result.status == "ok"
    assert len(result.inputs) == 1
    assert result.inputs[0].source == "binance"
