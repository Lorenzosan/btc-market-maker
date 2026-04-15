#pragma once

#include <unordered_map>
#include <vector>
#include <utility>

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

private:
    std::unordered_map<double, double> m_bids;
    std::unordered_map<double, double> m_asks;
};

} // namespace btc_mm
