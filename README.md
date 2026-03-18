# BTC Market Maker Take Home

This service ingests live BTC spot market data from Binance and Coinbase, maintains a local order book per venue, computes a consolidated fair value, and emits quote recommendations for a simple market making strategy.

The implementation prioritizes correctness, clarity, and robustness over complexity.

---

## Requirements

- Python 3.11+
- Internet access

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt