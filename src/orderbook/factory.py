from src.orderbook.book import OrderBook as PythonOrderBook
from src.orderbook.native import NativeOrderBook


def create_order_book(backend: str = "python"):
    if backend == "cpp":
        if NativeOrderBook is None:
            raise RuntimeError("C++ order book backend not available")
        return NativeOrderBook()

    if backend == "python":
        return PythonOrderBook()

    raise ValueError(f"unsupported backend: {backend}")
