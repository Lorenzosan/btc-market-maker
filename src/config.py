# ============================================
# Market data endpoints
# ============================================

# Binance websocket diff-depth stream for BTCUSDT.
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@depth@100ms"

# Binance REST endpoint for initial order book snapshot.
BINANCE_REST_SNAPSHOT_URL = "https://api.binance.com/api/v3/depth"

# Coinbase public websocket endpoint.
COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"

# Coinbase public REST book endpoint.
COINBASE_REST_BOOK_URL = "https://api.exchange.coinbase.com/products/{product_id}/book"


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
# 2 = per-event detailed JSON
OUTPUT_VERBOSITY = 0

# Reporting interval for compact mode.
OUTPUT_INTERVAL_SECONDS = 0.25


# ============================================
# Fair value configuration
# ============================================

# Maximum allowed spread in basis points for a venue to be included.
FAIR_VALUE_MAX_SPREAD_BPS = 3.0

# Maximum venue deviation from the cross-venue median mid in basis points.
FAIR_VALUE_MAX_DEVIATION_BPS = 8.0

# Minimum visible size used by the fair-value weighting model.
FAIR_VALUE_MIN_TOP_LEVEL_SIZE = 0.0001

# Maximum allowed time since last applied update before a venue is stale.
VENUE_STALE_AFTER_SECONDS = 1.5

# Do not use a venue in fair value immediately after it has been resynced.
# This avoids trusting a venue that only just recovered from a suspect state.
FAIR_VALUE_EXCLUDE_AFTER_RESYNC_SECONDS = 5.0

# Additional penalty applied to a venue that is tagged as lower confidence.
# Lower values reduce influence without fully excluding the venue.
FAIR_VALUE_LOW_CONFIDENCE_PENALTY = 0.35


# ============================================
# Market health and suppression
# ============================================

# Optional: controls whether quote debug internals are exposed in verbose output.
QUOTE_INCLUDE_DEBUG_FIELDS = True

# If cross-venue disagreement exceeds this threshold, quotes are suppressed.
QUOTE_SUPPRESS_MAX_DISAGREEMENT_BPS = 10.0

# If only one venue is available and it is a low-confidence venue, suppress quotes.
QUOTE_SUPPRESS_SINGLE_LOW_CONFIDENCE = True

# Cross-venue synthetic top-of-book can appear crossed because venues are
# asynchronous or materially disagree. This is not treated as local corruption.
QUOTE_SUPPRESS_CROSSED_MARKET = False


# ============================================
# Coinbase recovery configuration
# ============================================

# REST book level for Coinbase resync.
COINBASE_REST_BOOK_LEVEL = 2

# Periodic Coinbase resync interval.
COINBASE_RESYNC_INTERVAL_SECONDS = 15.0

# If the manager detects a suspicious Coinbase state, it will stop applying
# incremental Coinbase updates until a fresh snapshot arrives.
COINBASE_QUARANTINE_ON_CROSSED_BOOK = True


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

# Minimum half-spread in USD around the reservation price.
QUOTE_MIN_HALF_SPREAD = 1.5

# Additional half-spread applied per basis point of venue disagreement.
QUOTE_DISAGREEMENT_SPREAD_PER_BPS = 0.25

# Inventory skew in USD at full inventory utilization.
QUOTE_INVENTORY_SKEW = 8.0

# Spread multiplier when only one venue is usable.
QUOTE_DEGRADED_SPREAD_MULTIPLIER = 1.75

# Small price buffer used when clamping quotes away from the live market.
QUOTE_MARKET_EDGE_BUFFER = 0.01


# ============================================
# Quote engine: sizing
# ============================================

# Base maximum quote size in BTC under good conditions.
QUOTE_BASE_SIZE = 0.01

# Size multiplier in degraded single-venue mode.
QUOTE_DEGRADED_SIZE_MULTIPLIER = 0.5

# Minimum size as a fraction of base size.
QUOTE_MIN_SIZE_FACTOR = 0.2

# Fraction of visible top-of-book liquidity used as a cap on quote size.
QUOTE_LIQUIDITY_PARTICIPATION = 0.25

# Minimum absolute quote size in BTC after all sizing logic.
# Quotes below this threshold are suppressed or that side is disabled.
QUOTE_MIN_ABSOLUTE_SIZE = 0.0005

# Target trusted spread in basis points for full-size quoting.
# Wider trusted spreads reduce quote size, but only down to a floor.
QUOTE_SIZE_SPREAD_TARGET_BPS = 25.0

# Minimum spread-based size factor.
QUOTE_SIZE_MIN_SPREAD_FACTOR = 0.35

# Maximum disagreement in basis points for size scaling.
# At or above this level the disagreement factor reaches its floor.
QUOTE_SIZE_MAX_DISAGREEMENT_BPS = 8.0

# Minimum disagreement-based size factor before hard suppression kicks in.
QUOTE_SIZE_MIN_DISAGREEMENT_FACTOR = 0.40

# Health-based size multipliers.
QUOTE_SIZE_HEALTHY_MULTIPLIER = 1.0
QUOTE_SIZE_DEGRADED_MULTIPLIER = 0.7
QUOTE_SIZE_UNHEALTHY_MULTIPLIER = 0.0
