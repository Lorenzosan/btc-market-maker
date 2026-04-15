#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "order_book.h"

namespace py = pybind11;

PYBIND11_MODULE(_cpp_orderbook, m) {
    py::class_<btc_mm::OrderBook>(m, "OrderBook")
        .def(py::init<>())

        .def("apply_snapshot", &btc_mm::OrderBook::apply_snapshot)
        .def("apply_update", &btc_mm::OrderBook::apply_update)

        .def(
            "best_bid",
            [](const btc_mm::OrderBook& book) -> py::object {
                if (!book.has_best_bid()) {
                    return py::none();
                }
                return py::cast(book.best_bid());
            }
        )
        .def(
            "best_ask",
            [](const btc_mm::OrderBook& book) -> py::object {
                if (!book.has_best_ask()) {
                    return py::none();
                }
                return py::cast(book.best_ask());
            }
        )

        .def("is_crossed", &btc_mm::OrderBook::is_crossed);
}
