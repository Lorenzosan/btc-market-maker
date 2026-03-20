from src.fair_value.fair_value import FairValueEngine
from src.orderbook.manager import OrderBookManager
from src.types import MarketDataEvent


def make_snapshot(source: str, symbol: str, bid: tuple[float, float], ask: tuple[float, float]):
    return MarketDataEvent(
        source=source,
        symbol=symbol,
        channel="depth",
        event_type="snapshot",
        exchange_ts=None,
        received_ts="2026-03-20T12:00:00Z",
        sequence=1 if source == "binance" else None,
        bid_updates=[bid],
        ask_updates=[ask],
        raw={},
    )


def test_compute_returns_none_when_no_usable_venues():
    manager = OrderBookManager()
    engine = FairValueEngine()

    result = engine.compute(manager)

    assert result.fair_value is None
    assert result.status == "no_usable_venues"
    assert result.inputs == []
    assert result.excluded_inputs == []
    assert result.market_health == "unhealthy"
    assert result.confidence_profile == "none"


def test_coinbase_weight_is_penalized_vs_binance():
    manager = OrderBookManager()
    manager.apply_event(make_snapshot("binance", "BTCUSDT", (100.0, 10.0), (100.2, 10.0)))
    manager.apply_event(make_snapshot("coinbase", "BTC-USD", (100.0, 10.0), (100.2, 10.0)))

    engine = FairValueEngine(max_spread_bps=50.0, low_confidence_penalty=0.25)
    result = engine.compute(manager)

    assert len(result.inputs) == 2

    by_source = {quote.source: quote for quote in result.inputs}
    assert by_source["binance"].weight > by_source["coinbase"].weight
    assert by_source["binance"].confidence == "high"
    assert by_source["coinbase"].confidence == "low"
    assert result.market_health == "healthy"
    assert result.confidence_profile == "mixed"


def test_recently_resynced_venue_is_temporarily_excluded():
    manager = OrderBookManager()

    manager.apply_event(make_snapshot("binance", "BTCUSDT", (100.0, 5.0), (100.2, 5.0)))

    coinbase_state = manager.get_state("coinbase")
    manager.apply_event(make_snapshot("coinbase", "BTC-USD", (100.0, 5.0), (100.2, 5.0)))
    coinbase_state.last_resync_monotonic = coinbase_state.last_update_monotonic

    engine = FairValueEngine(max_spread_bps=50.0, exclude_after_resync_seconds=30.0)
    result = engine.compute(manager)

    assert result.status == "single_venue_only"
    assert len(result.inputs) == 1
    assert result.inputs[0].source == "binance"
    assert len(result.excluded_inputs) == 1
    assert result.excluded_inputs[0].source == "coinbase"
    assert result.excluded_inputs[0].excluded_reason == "recent_resync_cooldown"
    assert result.market_health == "degraded"
    assert result.confidence_profile == "high_only"


def test_compute_filters_all_venues_when_two_remaining_venues_are_too_far_apart():
    manager = OrderBookManager()
    manager.apply_event(make_snapshot("binance", "BTCUSDT", (100.0, 5.0), (100.2, 5.0)))
    manager.apply_event(make_snapshot("coinbase", "BTC-USD", (110.0, 5.0), (110.2, 5.0)))

    engine = FairValueEngine(max_spread_bps=50.0, max_deviation_bps=20.0)
    result = engine.compute(manager)

    assert result.fair_value is None
    assert result.status == "all_venues_filtered"
    assert result.market_health == "unhealthy"
    assert result.confidence_profile == "none"
    assert len(result.inputs) == 0
    assert len(result.excluded_inputs) == 2
    assert {quote.source for quote in result.excluded_inputs} == {"binance", "coinbase"}
    assert all(quote.excluded_reason == "mid_outlier" for quote in result.excluded_inputs)

def test_single_low_confidence_venue_status_is_explicit():
    manager = OrderBookManager()
    manager.apply_event(make_snapshot("coinbase", "BTC-USD", (100.0, 1.0), (100.2, 1.0)))

    engine = FairValueEngine(max_spread_bps=50.0)
    result = engine.compute(manager)

    assert result.status == "single_low_confidence_venue"
    assert result.market_health == "unhealthy"
    assert result.confidence_profile == "low_only"
    assert result.low_confidence_source_count == 1
    assert result.fair_value == 100.1
