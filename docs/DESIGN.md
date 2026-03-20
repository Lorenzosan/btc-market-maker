# Design Note

## Objectives

The goal is to construct a market-making system that:
- operates on imperfect real-time market data
- produces stable and explainable quotes
- handles degraded data conditions safely

---

## Venue Handling

### Binance

Binance is treated as the higher-confidence venue because:
- diff streams provide sequence-based updates
- snapshot bridging ensures continuity
- order book consistency can be verified

### Coinbase

Coinbase is handled in best-effort mode:
- no strict sequencing guarantees are assumed
- relies on level2 updates
- periodic REST resync is required

After resync or suspicious states:
- Coinbase is temporarily excluded or down-weighted

In practice:
- Binance drives price discovery
- Coinbase provides auxiliary information

---

## Order Book Integrity

Each venue is tracked independently with:
- initialization state
- staleness detection
- resync requirement flags

Local corruption (e.g. crossed book) is handled per venue.

Cross-venue inconsistencies are not treated as corruption.

In particular, a negative synthetic spread (best bid greater than best ask across venues) is not treated as a crossed market. This condition can arise from asynchronous updates or temporary disagreement between venues.

---

## Fair Value Computation

### Filtering

Venues are excluded if:
- spread is too wide
- data is stale
- recently resynced
- mid price deviates too far from the cross-venue median

Recently resynchronized venues are temporarily excluded to avoid trusting data immediately after recovery from a potentially inconsistent state.

### Weighting

Remaining venues are weighted using:
- inverse spread (tighter markets are preferred)
- top-of-book liquidity
- a confidence penalty for lower-trust venues

In practice, Binance typically dominates the fair value due to tighter spreads and larger visible size. Coinbase contributes but does not dominate.

### Cross-venue disagreement

Disagreement is measured in basis points.

It is used for:
- filtering in extreme cases
- spread widening
- quote size reduction

Cross-venue disagreement is not treated as book corruption. Instead, it is handled as a degradation of market quality.

---

## Market Health

Market health reflects usability of the data:

- healthy
  - at least one high-confidence venue available
  - disagreement within acceptable bounds

- degraded
  - elevated disagreement
  - or only a single venue available

- unhealthy
  - no usable venues
  - or only low-confidence venue

Market health affects quoting behavior but is separate from venue confidence.

---

## Quote Construction

### Reservation price

Reservation price is adjusted by inventory:

reservation_price = fair_value - inventory_utilization * skew

Long inventory lowers quotes, short inventory raises them.

---

### Spread

Spread is determined by:
- minimum configured spread
- observed market spread
- disagreement penalty

Single-venue scenarios widen spreads.

---

### Size

Quote size is determined heuristically as:

size = liquidity_cap × health_factor × spread_factor × disagreement_factor

Where:

- liquidity_cap  
  based on top-of-book size of the highest-confidence active venue

- health_factor  
  reduces size in degraded conditions

- spread_factor  
  reduces size when spreads are wide

- disagreement_factor  
  reduces size when venues diverge

Using only the highest-confidence venue for liquidity prevents a weak venue with small size from collapsing quote size.

---

### Inventory handling

Inventory affects:
- reservation price (global shift)
- side asymmetry (reduce size on risk-increasing side)

Inventory is not applied as a strong global size reduction to avoid double-counting risk and unintentionally suppressing both sides.

---

### Quote suppression

Quoting is disabled when:
- no fair value is available
- only a low-confidence venue is available
- disagreement exceeds threshold
- market health is unhealthy

---

## Design Tradeoffs

The system prioritizes:
- simplicity over complexity
- deterministic heuristics over predictive models
- explicit failure handling over implicit assumptions

It is not optimized for:
- PnL maximization
- latency arbitrage
- predictive signals

---

## Possible Extensions

- dynamic venue trust scoring
- latency-aware weighting
- external reference prices (e.g. perpetual futures)
- quote quality evaluation (markouts)
- lightweight fair value smoothing

---

## Summary

The system separates:
- venue trust from market condition
- local book integrity from cross-venue disagreement
- pricing from predictive modeling
