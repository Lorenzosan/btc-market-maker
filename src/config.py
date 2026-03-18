# Binance diff depth websocket. We keep 100 ms updates for lower latency.
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@depth@100ms"

# Binance REST snapshot used to correctly initialize the local order book.
BINANCE_REST_SNAPSHOT_URL = "https://api.binance.com/api/v3/depth"

COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"

BINANCE_SYMBOL = "BTCUSDT"
COINBASE_SYMBOL = "BTC-USD"
