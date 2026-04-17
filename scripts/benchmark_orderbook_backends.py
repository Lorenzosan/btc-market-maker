from pathlib import Path
import sys
import time
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.orderbook.manager import OrderBookManager
from src.types import MarketDataEvent

def make_snapshot(source: str) -> MarketDataEvent:
    symbol = "BTCUSDT" if source == "binance" else "BTC-USD"
    channel = "depth" if source == "binance" else "level2"

    exchange_ts = 0.0 if source == "binance" else "2026-03-20T12:00:00Z"

    return MarketDataEvent(
        source=source,
        symbol=symbol,
        channel=channel,
        event_type="snapshot",
        exchange_ts=exchange_ts,
        received_ts="2026-03-20T12:00:00Z",
        sequence=1 if source == "binance" else None,
        bid_updates=[
            (100.00, 1.0),
            (99.50, 2.0),
            (99.00, 3.0),
            (98.50, 4.0),
            (98.00, 5.0),
        ],
        ask_updates=[
            (100.50, 1.5),
            (101.00, 2.5),
            (101.50, 3.5),
            (102.00, 4.5),
            (102.50, 5.5),
        ],
    )


def make_binance_update(i: int) -> MarketDataEvent:
    base_bid = 100.00 - (i % 10) * 0.01
    base_ask = 100.50 + (i % 10) * 0.01

    return MarketDataEvent(
        source="binance",
        symbol="BTCUSDT",
        channel="depth",
        event_type="update",
        exchange_ts=float(i),
        received_ts=f"2026-03-20T12:00:{i % 60:02d}Z",
        sequence=2 + i,
        bid_updates=[
            (round(base_bid, 2), 1.0 + (i % 7) * 0.1),
            (round(99.50 - (i % 5) * 0.01, 2), 2.0 + (i % 3) * 0.2),
            (round(98.00 - (i % 4) * 0.01, 2), 0.0 if i % 11 == 0 else 5.0),
        ],
        ask_updates=[
            (round(base_ask, 2), 1.5 + (i % 5) * 0.1),
            (round(101.00 + (i % 3) * 0.01, 2), 2.5 + (i % 4) * 0.2),
            (round(102.50 + (i % 6) * 0.01, 2), 0.0 if i % 13 == 0 else 5.5),
        ],
    )


def make_coinbase_update(i: int) -> MarketDataEvent:
    base_bid = 100.00 - (i % 10) * 0.01
    base_ask = 100.50 + (i % 10) * 0.01

    return MarketDataEvent(
        source="coinbase",
        symbol="BTC-USD",
        channel="level2",
        event_type="update",
        exchange_ts=f"2026-03-20T12:01:{i % 60:02d}Z",
        received_ts=f"2026-03-20T12:01:{i % 60:02d}Z",
        sequence=None,
        bid_updates=[
            (round(base_bid, 2), 1.0 + (i % 7) * 0.1),
            (round(99.50 - (i % 5) * 0.01, 2), 2.0 + (i % 3) * 0.2),
            (round(98.00 - (i % 4) * 0.01, 2), 0.0 if i % 11 == 0 else 5.0),
        ],
        ask_updates=[
            (round(base_ask, 2), 1.5 + (i % 5) * 0.1),
            (round(101.00 + (i % 3) * 0.01, 2), 2.5 + (i % 4) * 0.2),
            (round(102.50 + (i % 6) * 0.01, 2), 0.0 if i % 13 == 0 else 5.5),
        ],
    )


def build_events(num_updates: int) -> list[MarketDataEvent]:
    events: list[MarketDataEvent] = [
        make_snapshot("binance"),
        make_snapshot("coinbase"),
    ]

    for i in range(num_updates):
        events.append(make_binance_update(i))
        events.append(make_coinbase_update(i))

    return events


def run_backend(events: list[MarketDataEvent], backend: str) -> float:
    manager = OrderBookManager(backend=backend)

    start = time.perf_counter()

    for event in events:
        manager.apply_event(event)

    elapsed = time.perf_counter() - start

    bn_top = manager.top_of_book("binance", now_monotonic=0.0)
    cb_top = manager.top_of_book("coinbase", now_monotonic=0.0)

    if bn_top["best_bid"] is None or bn_top["best_ask"] is None:
        raise RuntimeError(f"{backend} backend ended with invalid Binance top of book")

    if cb_top["best_bid"] is None or cb_top["best_ask"] is None:
        raise RuntimeError(f"{backend} backend ended with invalid Coinbase top of book")

    return elapsed


def benchmark(num_updates: int, repeats: int) -> None:
    events = build_events(num_updates)

    python_times = []
    cpp_times = []

    for _ in range(repeats):
        python_times.append(run_backend(events, "python"))
        cpp_times.append(run_backend(events, "cpp"))

    python_avg = mean(python_times)
    cpp_avg = mean(cpp_times)

    total_events = len(events)
    python_eps = total_events / python_avg
    cpp_eps = total_events / cpp_avg
    speedup = python_avg / cpp_avg

    print(f"events per run: {total_events}")
    print(f"repeats:        {repeats}")
    print()
    print(f"python avg:     {python_avg:.6f} s")
    print(f"cpp avg:        {cpp_avg:.6f} s")
    print(f"python eps:     {python_eps:,.0f} events/s")
    print(f"cpp eps:        {cpp_eps:,.0f} events/s")
    print(f"speedup:        {speedup:.2f}x")


if __name__ == "__main__":
    benchmark(num_updates=100_000, repeats=5)
