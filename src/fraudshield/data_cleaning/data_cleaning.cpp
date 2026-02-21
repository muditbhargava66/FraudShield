// src/fraudshield/data_cleaning/data_cleaning.cpp

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <numeric>
#include <cmath>
#include <limits>

namespace py = pybind11;

class DataCleaning {
public:
    static void remove_missing_values(std::vector<double>& data) {
        data.erase(std::remove_if(data.begin(), data.end(), [](double value) { return std::isnan(value); }), data.end());
    }

    static double calculate_mean(const std::vector<double>& data) {
        if (data.empty()) {
            throw std::invalid_argument("Data vector is empty.");
        }
        double sum = std::accumulate(data.begin(), data.end(), 0.0);
        return sum / data.size();
    }

    static double calculate_stddev(const std::vector<double>& data, double mean) {
        if (data.empty()) {
            throw std::invalid_argument("Data vector is empty.");
        }
        if (data.size() < 2) {
            return 0.0;
        }
        double sq_sum = 0.0;
        for (std::vector<double>::const_iterator it = data.begin(); it != data.end(); ++it) {
            double diff = *it - mean;
            sq_sum += diff * diff;
        }
        // Use sample standard deviation (n-1) instead of population (n)
        return std::sqrt(sq_sum / (data.size() - 1));
    }

    struct OutlierPredicate {
        double mean;
        double stddev;
        double threshold;
        OutlierPredicate(double mean, double stddev, double threshold)
            : mean(mean), stddev(stddev), threshold(threshold) {}
        bool operator()(double value) const {
            return std::abs(value - mean) > threshold * stddev;
        }
    };

    static void remove_outliers(std::vector<double>& data, double threshold) {
        if (data.empty()) {
            return;
        }
        double mean = calculate_mean(data);
        double stddev = calculate_stddev(data, mean);
        if (stddev == 0.0) {
            return;
        }
        data.erase(std::remove_if(data.begin(), data.end(), OutlierPredicate(mean, stddev, threshold)), data.end());
    }
};

// Python bindings using pybind11
py::array_t<double> remove_missing_values_py(py::array_t<double> input) {
    py::buffer_info buf = input.request();
    double* ptr = static_cast<double*>(buf.ptr);
    size_t total = buf.size;
    
    std::vector<double> data_vec(ptr, ptr + total);
    DataCleaning::remove_missing_values(data_vec);
    
    // Create output array with cleaned data
    py::array_t<double> result(data_vec.size());
    py::buffer_info result_buf = result.request();
    double* result_ptr = static_cast<double*>(result_buf.ptr);
    std::copy(data_vec.begin(), data_vec.end(), result_ptr);
    
    return result;
}

py::array_t<double> remove_outliers_py(py::array_t<double> input, double threshold) {
    py::buffer_info buf = input.request();
    double* ptr = static_cast<double*>(buf.ptr);
    size_t total = buf.size;
    
    std::vector<double> data_vec(ptr, ptr + total);
    DataCleaning::remove_outliers(data_vec, threshold);
    
    // Create output array with cleaned data
    py::array_t<double> result(data_vec.size());
    py::buffer_info result_buf = result.request();
    double* result_ptr = static_cast<double*>(result_buf.ptr);
    std::copy(data_vec.begin(), data_vec.end(), result_ptr);
    
    return result;
}

PYBIND11_MODULE(_data_cleaning_cpp, m) {
    m.doc() = "C++ data cleaning module for FraudShield";
    
    m.def("remove_missing_values", &remove_missing_values_py,
          "Remove missing (NaN) values from array",
          py::arg("input"));
    
    m.def("remove_outliers", &remove_outliers_py,
          "Remove outliers using z-score threshold",
          py::arg("input"), py::arg("threshold") = 3.0);
}

// int main() {
//     // Example usage of DataCleaning class
//     double arr[] = {1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 15.0, 20.0};
//     std::vector<double> data(arr, arr + sizeof(arr) / sizeof(arr[0]));

//     std::cout << "Original data: ";
//     for (std::vector<double>::const_iterator it = data.begin(); it != data.end(); ++it) {
//         std::cout << *it << " ";
//     }
//     std::cout << std::endl;

//     DataCleaning::remove_missing_values(data);
//     DataCleaning::remove_outliers(data, 2.0);

//     std::cout << "Cleaned data: ";
//     for (std::vector<double>::const_iterator it = data.begin(); it != data.end(); ++it) {
//         std::cout << *it << " ";
//     }
//     std::cout << std::endl;

//     return 0;
// }
