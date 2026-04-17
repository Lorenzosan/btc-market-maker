#include "order_book.h"

#include <cstddef>
#include <stdexcept>

namespace btc_mm {

void OrderBook::apply_snapshot(
    const std::vector<PriceLevel>& bid_updates,
    const std::vector<PriceLevel>& ask_updates
) {
    m_bids.clear();
    m_asks.clear();

    for (const auto& [price, size] : bid_updates) {
        if (size > 0.0) {
            m_bids[price] = size;
        }
    }

    for (const auto& [price, size] : ask_updates) {
        if (size > 0.0) {
            m_asks[price] = size;
        }
    }
}

void OrderBook::apply_update(
    const std::vector<PriceLevel>& bid_updates,
    const std::vector<PriceLevel>& ask_updates
) {
    for (const auto& [price, size] : bid_updates) {
        if (size == 0.0) {
            m_bids.erase(price);
        } else {
            m_bids[price] = size;
        }
    }

    for (const auto& [price, size] : ask_updates) {
        if (size == 0.0) {
            m_asks.erase(price);
        } else {
            m_asks[price] = size;
        }
    }
}

bool OrderBook::has_best_bid() const {
    return !m_bids.empty();
}

bool OrderBook::has_best_ask() const {
    return !m_asks.empty();
}

PriceLevel OrderBook::best_bid() const {
    if (m_bids.empty()) {
        throw std::runtime_error("best_bid called on empty bid book");
    }

    const auto& [price, size] = *m_bids.begin();
    return {price, size};
}

PriceLevel OrderBook::best_ask() const {
    if (m_asks.empty()) {
        throw std::runtime_error("best_ask called on empty ask book");
    }

    const auto& [price, size] = *m_asks.begin();
    return {price, size};
}

bool OrderBook::is_crossed() const {
    if (m_bids.empty() || m_asks.empty()) {
        return false;
    }

    return m_bids.begin()->first >= m_asks.begin()->first;
}

std::size_t OrderBook::bid_count() const {
    return m_bids.size();
}

} // namespace btc_mm
