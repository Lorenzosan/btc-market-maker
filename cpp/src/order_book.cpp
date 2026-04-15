#include "order_book.h"

#include <algorithm>
#include <stdexcept>

namespace btc_mm {

void OrderBook::apply_snapshot(
    const std::vector<PriceLevel>& bid_updates,
    const std::vector<PriceLevel>& ask_updates
) {
    m_bids.clear();
    m_asks.clear();

    for (const auto& level : bid_updates) {
        const auto& [price, size] = level;
        if (size > 0.0) {
            m_bids[price] = size;
        }
    }

    for (const auto& level : ask_updates) {
        const auto& [price, size] = level;
        if (size > 0.0) {
            m_asks[price] = size;
        }
    }
}

void OrderBook::apply_update(
    const std::vector<PriceLevel>& bid_updates,
    const std::vector<PriceLevel>& ask_updates
) {
    for (const auto& level : bid_updates) {
        const auto& [price, size] = level;
        if (size == 0.0) {
            m_bids.erase(price);
        } else {
            m_bids[price] = size;
        }
    }

    for (const auto& level : ask_updates) {
        const auto& [price, size] = level;
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

    auto it = std::max_element(
        m_bids.begin(),
        m_bids.end(),
        [](const auto& a, const auto& b) {
            return a.first < b.first;
        }
    );

    return {it->first, it->second};
}

PriceLevel OrderBook::best_ask() const {
    if (m_asks.empty()) {
        throw std::runtime_error("best_ask called on empty ask book");
    }

    auto it = std::min_element(
        m_asks.begin(),
        m_asks.end(),
        [](const auto& a, const auto& b) {
            return a.first < b.first;
        }
    );

    return {it->first, it->second};
}

bool OrderBook::is_crossed() const {
    if (m_bids.empty() || m_asks.empty()) {
        return false;
    }

    auto bid = best_bid();
    auto ask = best_ask();
    return bid.first >= ask.first;
}

} // namespace mm
