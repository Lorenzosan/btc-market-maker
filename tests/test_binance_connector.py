from collections import deque

import pytest

from src.ingestion.binance import BinanceConnector
from src.types import MarketDataEvent


def make_snapshot(last_update_id: int) -> MarketDataEvent:
    return MarketDataEvent(
        source="binance",
        symbol="BTCUSDT",
        channel="depth",
        event_type="snapshot",
        exchange_ts=None,
        received_ts="2026-03-19T00:00:00+00:00",
        sequence=last_update_id,
        bid_updates=[(100.0, 1.0)],
        ask_updates=[(101.0, 1.0)],
        raw={},
    )


def test_drop_stale_buffered_events_keeps_first_bridging_event():
    connector = BinanceConnector()
    buffered_events = deque(
        [
            {"U": 95, "u": 100, "b": [], "a": [], "E": 1},
            {"U": 100, "u": 105, "b": [], "a": [], "E": 2},
            {"U": 106, "u": 110, "b": [], "a": [], "E": 3},
        ]
    )

    connector.drop_stale_buffered_events(buffered_events, last_update_id=100)

    assert len(buffered_events) == 2
    assert buffered_events[0]["U"] == 100
    assert buffered_events[0]["u"] == 105


def test_validate_snapshot_bridge_accepts_covering_first_event():
    connector = BinanceConnector()
    buffered_events = deque(
        [
            {"U": 100, "u": 105, "b": [], "a": [], "E": 2},
            {"U": 106, "u": 110, "b": [], "a": [], "E": 3},
        ]
    )

    connector.validate_snapshot_bridge(buffered_events, last_update_id=100)


def test_validate_snapshot_bridge_rejects_non_covering_first_event():
    connector = BinanceConnector()
    buffered_events = deque(
        [
            {"U": 106, "u": 110, "b": [], "a": [], "E": 2},
        ]
    )

    with pytest.raises(RuntimeError, match="does not bridge"):
        connector.validate_snapshot_bridge(buffered_events, last_update_id=100)


@pytest.mark.asyncio
async def test_initialize_from_snapshot_retries_until_bridge_is_possible(monkeypatch):
    connector = BinanceConnector()
    buffered_events = deque(
        [
            {"U": 105, "u": 110, "b": [], "a": [], "E": 1},
            {"U": 111, "u": 115, "b": [], "a": [], "E": 2},
        ]
    )

    snapshots = iter([make_snapshot(100), make_snapshot(104)])

    def fake_fetch_snapshot_event():
        return next(snapshots)

    monkeypatch.setattr(connector, "fetch_snapshot_event", fake_fetch_snapshot_event)

    snapshot, last_update_id = await connector.initialize_from_snapshot(
        buffered_events,
        max_attempts=2,
    )

    assert snapshot.sequence == 104
    assert last_update_id == 104
    assert buffered_events[0]["U"] == 105
    assert buffered_events[0]["u"] == 110
