try:
    from _cpp_orderbook import OrderBook as NativeOrderBook
except ImportError:
    NativeOrderBook = None
