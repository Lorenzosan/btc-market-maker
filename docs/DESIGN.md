
---

## DESIGN.md

```markdown
# Design Note

## Objectives

The goal is to construct a simple but robust market-making system that:
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
- no strict sequencing guarantees
- relies on level2 updates
- periodic REST resync is required

After resync or suspicious states:
- Coinbase is temporarily excluded or down-weighted

Conclusion:
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

---

## Fair Value Computation

### Filtering

Venues are excluded if:
- spread is too wide
- data is stale
- recently resynced
- mid price deviates too far from cross-venue median

### Weighting

Remaining venues are weighted by:
- relative spread (tighter is better)
- top-of-book liquidity
- confidence penalty

### Cross-venue disagreement

Disagreement is measured in basis points.

It is used for:
- filtering (extreme cases)
- spread widening
- size reduction

Important:
A negative synthetic spread (best bid > best ask across venues) is **not treated as a crossed market**, but as asynchronous or disagreeing venues.

---

## Market Health

Market health reflects usability of the data:

- **healthy**
  - multiple venues
  - low disagreement

- **degraded**
  - elevated disagreement
  - or single high-confidence venue

- **unhealthy**
  - no usable venues
  - or only low-confidence venue

Health influences quoting behavior but is separate from venue confidence.

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

Quote size is determined as:

size = liquidity_cap × health × spread_factor × disagreement_factor

Where:

- **liquidity_cap**
  - based on top-of-book size of highest-confidence venue

- **health factor**
  - reduces size in degraded conditions

- **spread factor**
  - reduces size when spreads are wide

- **disagreement factor**
  - reduces size when venues diverge

Inventory does **not** reduce total size globally, only skews sides.

---

### Inventory handling

Inventory affects:
- reservation price (global shift)
- side asymmetry (reduce size on risk-increasing side)

It does not suppress both sides simultaneously.

---

### Quote suppression

Quoting is disabled when:
- no fair value
- only low-confidence venue available
- disagreement exceeds threshold
- market health is unhealthy

---

## Design Tradeoffs

- Simplicity over complexity
- Deterministic heuristics over predictive models
- Explicit failure handling over implicit assumptions

The system is intentionally not optimized for:
- PnL maximization
- latency arbitrage
- predictive signals

---

## Possible Extensions

- latency-aware weighting
- external reference prices (e.g. perpetual futures)
- quote performance evaluation (markouts)
- smoothing of fair value

These were not implemented to keep the system transparent.

---

## Summary

The system:
- prioritizes data reliability over model sophistication
- separates venue trust from market condition
- produces stable and explainable quotes

The result is a robust baseline market-making engine suitable for extension.