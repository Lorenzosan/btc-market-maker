from pathlib import Path
import sys
import time
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.orderbook.book import OrderBook as PythonOrderBook
from _cpp_orderbook import OrderBook as CppOrderBook


def build_snapshot():
    bids = [
        (100.00, 1.0),
        (99.50, 2.0),
        (99.00, 3.0),
        (98.50, 4.0),
        (98.00, 5.0),
    ]
    asks = [
        (100.50, 1.5),
        (101.00, 2.5),
        (101.50, 3.5),
        (102.00, 4.5),
        (102.50, 5.5),
    ]
    return bids, asks


def build_updates(num_updates: int):
    updates = []
    for i in range(num_updates):
        base_bid = 100.00 - (i % 10) * 0.01
        base_ask = 100.50 + (i % 10) * 0.01

        bid_updates = [
            (round(base_bid, 2), 1.0 + (i % 7) * 0.1),
            (round(99.50 - (i % 5) * 0.01, 2), 2.0 + (i % 3) * 0.2),
            (round(98.00 - (i % 4) * 0.01, 2), 0.0 if i % 11 == 0 else 5.0),
        ]
        ask_updates = [
            (round(base_ask, 2), 1.5 + (i % 5) * 0.1),
            (round(101.00 + (i % 3) * 0.01, 2), 2.5 + (i % 4) * 0.2),
            (round(102.50 + (i % 6) * 0.01, 2), 0.0 if i % 13 == 0 else 5.5),
        ]
        updates.append((bid_updates, ask_updates))
    return updates


def run_book(book_cls, updates, top_every: int) -> float:
    book = book_cls()
    bids, asks = build_snapshot()
    book.apply_snapshot(bids, asks)

    start = time.perf_counter()

    for i, (bid_updates, ask_updates) in enumerate(updates, start=1):
        book.apply_update(bid_updates, ask_updates)

        if i % top_every == 0:
            book.best_bid()
            book.best_ask()
            book.is_crossed()

    return time.perf_counter() - start


def benchmark(num_updates: int = 200_000, repeats: int = 5, top_every: int = 1) -> None:
    updates = build_updates(num_updates)

    py_times = []
    cpp_times = []

    for _ in range(repeats):
        py_times.append(run_book(PythonOrderBook, updates, top_every))
        cpp_times.append(run_book(CppOrderBook, updates, top_every))

    py_avg = mean(py_times)
    cpp_avg = mean(cpp_times)

    py_ops = num_updates / py_avg
    cpp_ops = num_updates / cpp_avg
    speedup = py_avg / cpp_avg

    print(f"updates per run: {num_updates}")
    print(f"repeats:         {repeats}")
    print(f"top_every:       {top_every}")
    print()
    print(f"python avg:      {py_avg:.6f} s")
    print(f"cpp avg:         {cpp_avg:.6f} s")
    print(f"python ups:      {py_ops:,.0f} updates/s")
    print(f"cpp ups:         {cpp_ops:,.0f} updates/s")
    print(f"speedup:         {speedup:.2f}x")


if __name__ == "__main__":
    benchmark(num_updates=200_000, repeats=5, top_every=1)
