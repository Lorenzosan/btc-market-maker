cmake_minimum_required(VERSION 3.18)
project(cpp_orderbook LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(pybind11 REQUIRED)

pybind11_add_module(_cpp_orderbook
    bindings/pybind_module.cpp
    src/order_book.cpp
)

target_include_directories(_cpp_orderbook
    PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)
