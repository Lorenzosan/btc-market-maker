# Design Note

## 1. Architecture Overview

The system ingests real-time BTC spot market data from multiple venues, maintains a local order book per venue, computes a consolidated fair value, and emits quote recommendations for a simple market making strategy.

The architecture is composed of four main components:

- Market data ingestion (per venue)
- Local order book management
- Fair value computation
- Quote generation

The system is designed to be event-driven, with exchange updates flowing through a central queue and applied to per-venue order books.

---

## 2. Order Book Construction

Each venue maintains an independent local order book.

### Snapshots

- A snapshot initializes the full book state
- Existing state is replaced entirely
- The book is marked as initialized only after a snapshot is received

### Incremental Updates

- Updates are applied as price-level deltas
- Each update consists of price and size
- Size equal to zero removes the level
- Non-zero size inserts or updates the level

### Validity Checks

- A book is considered invalid if:
  - it has not received a snapshot
  - best bid is greater than or equal to best ask (crossed book)

Invalid books are excluded from fair value computation.

### Exchange-Specific Handling

**Binance**
- Uses snapshot + diff stream
- Buffered updates are replayed after snapshot
- Sequence numbers are checked
- Gaps trigger a resynchronization

**Coinbase**
- Uses snapshot + level2 updates
- Updates are applied after snapshot
- No explicit sequence continuity validation is performed in this implementation

---

## 3. Fair Value Estimation

Fair value is computed as a weighted average of venue mid prices.

### Mid Price

For each valid venue:

mid = (best_bid + best_ask) / 2

### Weighting

Each venue is weighted by the inverse of its spread:

weight = 1 / spread

where:

spread = best_ask - best_bid

### Aggregation

fair_value = sum(mid_i * weight_i) / sum(weight_i)

### Filtering

A venue is excluded if:

- it is not initialized
- it has a crossed book
- spread is non-positive
- spread exceeds a fixed threshold (`MAX_FAIR_VALUE_SPREAD`)

### Rationale

- Inverse-spread weighting favors tighter and more liquid markets
- The method is simple, transparent, and robust enough for a baseline system

### Limitations

- No explicit freshness or staleness checks
- No outlier rejection when venues disagree
- No latency or timestamp weighting
- Fixed spread threshold is heuristic

---

## 4. Quote Logic

The system produces a recommended bid and ask based on fair value and inventory.

### Reservation Price

reservation_price = fair_value - inventory * inventory_skew

- Positive inventory shifts reservation price downward
- Negative inventory shifts it upward

### Quote Prices

bid = reservation_price - half_spread  
ask = reservation_price + half_spread

### Quote Sizes

- Fixed base size is used on both sides

### Inventory Constraints

- If inventory >= max_inventory:
  - bid side is disabled
- If inventory <= -max_inventory:
  - ask side is disabled

### Rationale

- Inventory skew encourages reversion toward neutral inventory
- Fixed spread ensures predictable quoting behavior

### Limitations

- No dynamic spread adjustment based on volatility or uncertainty
- No adaptive sizing
- No fill simulation or inventory updates from market interaction

---

## 5. Failure Modes

The system handles several failure scenarios.

### Exchange Connectivity

- Websocket disconnects trigger reconnect loops

### Binance Sequence Gaps

- Detected via sequence mismatch
- Trigger a full resync via snapshot reload

### Updates Before Snapshot

- Ignored
- Venue remains uninitialized

### Crossed Books

- Marked invalid
- Excluded from fair value

### No Valid Venues

- Fair value is unavailable
- Quoting is disabled

---

## 6. Assumptions

- Only public BTC spot order books are used
- Best bid and ask are sufficient for fair value estimation
- Inventory is maintained internally and is not updated from trades
- Exchange data is assumed to be reasonably timely
- Simplicity and robustness are prioritized over model sophistication

---

## 7. Intentionally Unhandled Edge Cases

The following are not handled in this implementation:

- No stale-data timeout per venue
- No clock synchronization or latency correction
- No detection of delayed or frozen feeds
- No advanced outlier filtering across venues
- No persistence or recovery after restart
- No replay or backtesting capability
- Coinbase sequence validation is weaker than Binance

These are acceptable omissions for a baseline implementation but would need to be addressed in production.

---

## 8. Production Improvements

If extended to production, the following changes would be required:

### Market Data

- Per-venue freshness checks
- Latency monitoring and feed health scoring
- Redundant data sources

### Fair Value

- Outlier rejection across venues
- Time-weighted or liquidity-weighted aggregation
- Volatility-aware adjustments

### Quoting

- Dynamic spreads based on risk and market conditions
- Adaptive sizing
- Integration with execution and fill tracking

### Infrastructure

- Structured logging and metrics
- Alerting on degraded states
- Persistent state and warm restart
- Containerization and deployment automation

### Testing

- Replay-based tests using recorded market data
- Integration tests across full pipeline

---

## Summary

This implementation provides a clean and functional baseline system for multi-venue market data aggregation, fair value computation, and quote generation.

The design favors clarity and correctness, while explicitly documenting limitations and areas for extension.