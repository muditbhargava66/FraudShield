cmake_minimum_required(VERSION 3.15...3.27)
project(fraudshield)

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(_data_cleaning_cpp src/fraudshield/data_cleaning/data_cleaning.cpp)
install(TARGETS _data_cleaning_cpp DESTINATION fraudshield/data_cleaning)

pybind11_add_module(_feature_engineering_cpp src/fraudshield/feature_engineering/feature_engineering.cpp)
install(TARGETS _feature_engineering_cpp DESTINATION fraudshield/feature_engineering)
