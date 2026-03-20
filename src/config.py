# ============================================
# Market data endpoints
# ============================================

# Binance websocket diff-depth stream for BTCUSDT (100 ms updates).
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@depth@100ms"

# Binance REST endpoint for initial order book snapshot.
BINANCE_REST_SNAPSHOT_URL = "https://api.binance.com/api/v3/depth"

# Coinbase public websocket endpoint.
COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"


# ============================================
# Instruments
# ============================================

# Symbols used for BTC spot books on each venue.
BINANCE_SYMBOL = "BTCUSDT"
COINBASE_SYMBOL = "BTC-USD"


# ============================================
# Output configuration
# ============================================

# Verbosity level:
# 0 = periodic compact summary
# 1 = per-event concise JSON
# 2 = per-event detailed JSON (includes fair-value inputs)
OUTPUT_VERBOSITY = 0

# Reporting interval for compact mode.
OUTPUT_INTERVAL_SECONDS = 0.5


# ============================================
# Fair value configuration
# ============================================

# Maximum allowed spread (USD) for a venue to be included in fair value.
# Wider books are considered unreliable.
FAIR_VALUE_MAX_SPREAD = 1.0

# Maximum allowed time since last update before a venue is considered stale.
# Stale venues are excluded from fair value.
VENUE_STALE_AFTER_SECONDS = 1.5


# ============================================
# Inventory limits
# ============================================

# Hard inventory bounds. Crossing these disables one side of quoting.
MAX_LONG_INVENTORY = 0.05
MAX_SHORT_INVENTORY = -0.05

# Initial simulated inventory.
INITIAL_INVENTORY = 0.0


# ============================================
# Quote engine: pricing
# ============================================

# Half-spread (USD) around reservation price in normal conditions.
QUOTE_HALF_SPREAD = 2.0

# Inventory skew (USD per BTC). Positive inventory shifts quotes downward.
QUOTE_INVENTORY_SKEW = 5.0

# Spread multiplier when only one venue is usable (degraded market).
QUOTE_DEGRADED_SPREAD_MULTIPLIER = 2.0


# ============================================
# Quote engine: sizing
# ============================================

# Base quote size (BTC).
QUOTE_BASE_SIZE = 0.01

# Size multiplier in degraded single-venue mode.
QUOTE_DEGRADED_SIZE_MULTIPLIER = 0.5

# Minimum size as a fraction of base size, regardless of inventory.
QUOTE_MIN_SIZE_FACTOR = 0.2

# Fraction of visible top-of-book liquidity used as a cap on quote size.
QUOTE_LIQUIDITY_PARTICIPATION = 0.25
