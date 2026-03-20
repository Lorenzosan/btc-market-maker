# BTC Market Making Engine

## Overview

This project implements a simplified BTC market-making system using public market data from Binance and Coinbase.

The system:
- Maintains local order books for each venue
- Computes a consolidated fair value
- Generates quote recommendations (bid/ask and size)
- Adapts to market conditions, venue health, and inventory

---

## Architecture

### Components

- **Connectors**
  - Binance (diff stream + snapshot sync)
  - Coinbase (best-effort level2 + periodic resync)

- **OrderBookManager**
  - Maintains local books per venue
  - Tracks staleness, resync state, and validity

- **FairValueEngine**
  - Filters unreliable venues
  - Computes weighted fair value
  - Outputs market diagnostics

- **QuoteEngine**
  - Computes reservation price
  - Generates bid/ask quotes
  - Adjusts spread and size dynamically

---

## Running the system

### Setup

```bash
python -m venv btc-venv
source btc-venv/bin/activate
pip install -r requirements.txt