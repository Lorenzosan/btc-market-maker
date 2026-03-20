# Binance websocket diff-depth stream for BTCUSDT.
# We use 100 ms updates to get reasonably fresh book updates.
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@depth@100ms"

# Binance REST endpoint used to fetch the initial snapshot.
# This is required for correct local-book initialization.
BINANCE_REST_SNAPSHOT_URL = "https://api.binance.com/api/v3/depth"

# Coinbase public websocket endpoint.
COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"

# Symbols used for the public BTC spot books.
BINANCE_SYMBOL = "BTCUSDT"
COINBASE_SYMBOL = "BTC-USD"

# Output verbosity:
# 0 = compact periodic summary
# 1 = per-event concise JSON
# 2 = per-event detailed JSON with fair-value inputs
OUTPUT_VERBOSITY = 0

# Reporting interval used in compact mode.
OUTPUT_INTERVAL_SECONDS = 0.5

# Quote-engine parameters.
# Base size is the default quote size on each side.
QUOTE_BASE_SIZE = 0.01

# Half-spread in USD around the reservation price.
QUOTE_HALF_SPREAD = 2.0

# Inventory skew in USD per BTC of inventory.
# Positive inventory shifts quotes downward to encourage selling.
QUOTE_INVENTORY_SKEW = 5.0

# Simple inventory limits used to disable one side when inventory is extreme.
MAX_LONG_INVENTORY = 0.05
MAX_SHORT_INVENTORY = -0.05

# Initial simulated inventory.
INITIAL_INVENTORY = 0.0

# Maximum allowed spread (in price units) for a venue to be included in fair value
# Venues with wider spreads are considered unreliable and excluded from the calculation
FAIR_VALUE_MAX_SPREAD = 1.0

# Maximum time since the last successfully applied venue update before the
# venue is considered stale and excluded from fair value.
VENUE_STALE_AFTER_SECONDS = 1.5

