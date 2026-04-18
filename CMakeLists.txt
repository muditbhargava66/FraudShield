cmake_minimum_required(VERSION 3.15...3.27)

project(fraudshield LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

find_package(pybind11 CONFIG REQUIRED)

function(fraudshield_add_extension target source install_subdir)
    pybind11_add_module(${target} ${source})
    target_compile_features(${target} PRIVATE cxx_std_17)

    if(MSVC)
        target_compile_options(${target} PRIVATE /W4)
    else()
        target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
    endif()

    install(TARGETS ${target} DESTINATION fraudshield/${install_subdir})
endfunction()

fraudshield_add_extension(
    _data_cleaning_cpp
    src/fraudshield/data_cleaning/data_cleaning.cpp
    data_cleaning
)

fraudshield_add_extension(
    _feature_engineering_cpp
    src/fraudshield/feature_engineering/feature_engineering.cpp
    feature_engineering
)
