#pragma once

#include <functional>
#include <map>
#include <utility>
#include <vector>

namespace btc_mm {

using Price = double;
using Size = double;
using PriceLevel = std::pair<Price, Size>;

class OrderBook {
public:
    OrderBook() = default;

    void apply_snapshot(
        const std::vector<PriceLevel>& bid_updates,
        const std::vector<PriceLevel>& ask_updates
    );

    void apply_update(
        const std::vector<PriceLevel>& bid_updates,
        const std::vector<PriceLevel>& ask_updates
    );

    PriceLevel best_bid() const;
    PriceLevel best_ask() const;

    bool has_best_bid() const;
    bool has_best_ask() const;
    bool is_crossed() const;

    std::size_t bid_count() const;

private:
    std::map<Price, Size, std::greater<Price>> m_bids;
    std::map<Price, Size> m_asks;
};

} // namespace btc_mm
