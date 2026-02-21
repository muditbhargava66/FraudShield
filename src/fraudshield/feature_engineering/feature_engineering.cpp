// src/fraudshield/feature_engineering/feature_engineering.cpp

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <iostream>
#include <vector>
#include <unordered_map>
#include <numeric>
#include <cmath>
#include <limits>

namespace py = pybind11;

class FeatureEngineering {
public:
    static std::vector<double> calculate_moving_average(const std::vector<double>& data, int window_size) {
        if (window_size <= 0 || static_cast<size_t>(window_size) > data.size()) {
            throw std::invalid_argument("Invalid window size.");
        }

        std::vector<double> moving_average(data.size() - window_size + 1);
        double sum = std::accumulate(data.begin(), data.begin() + window_size, 0.0);
        moving_average[0] = sum / window_size;

        for (size_t i = 1; i < moving_average.size(); ++i) {
            sum -= data[i - 1];
            // Bounds check: ensure i + window_size - 1 < data.size()
            size_t next_idx = i + window_size - 1;
            if (next_idx >= data.size()) {
                break;
            }
            sum += data[next_idx];
            moving_average[i] = sum / window_size;
        }

        return moving_average;
    }

    static std::vector<double> calculate_exponential_moving_average(const std::vector<double>& data, double alpha) {
        if (alpha < 0.0 || alpha > 1.0) {
            throw std::invalid_argument("Invalid alpha value.");
        }

        std::vector<double> ema(data.size());
        ema[0] = data[0];

        for (size_t i = 1; i < data.size(); ++i) {
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1];
        }

        return ema;
    }

    static std::vector<double> calculate_relative_strength_index(const std::vector<double>& data, int window_size) {
        if (window_size <= 0 || static_cast<size_t>(window_size) > data.size()) {
            throw std::invalid_argument("Invalid window size.");
        }
        // Handle edge case where window_size is 1
        if (window_size == 1) {
            throw std::invalid_argument("Window size must be at least 2 for RSI calculation.");
        }

        std::vector<double> rsi(data.size() - window_size + 1);
        std::vector<double> gains(window_size - 1, 0.0);
        std::vector<double> losses(window_size - 1, 0.0);

        for (int i = 1; i < window_size; ++i) {
            double diff = data[i] - data[i - 1];
            if (diff > 0) {
                gains[i - 1] = diff;
            } else {
                losses[i - 1] = -diff;
            }
        }

        double avg_gain = std::accumulate(gains.begin(), gains.end(), 0.0) / window_size;
        double avg_loss = std::accumulate(losses.begin(), losses.end(), 0.0) / window_size;

        double rs = (avg_loss == 0.0) ? std::numeric_limits<double>::infinity() : (avg_gain / avg_loss);
        rsi[0] = 100.0 - (100.0 / (1.0 + rs));

        for (size_t i = window_size; i < data.size(); ++i) {
            double diff = data[i] - data[i - 1];
            double gain = (diff > 0) ? diff : 0.0;
            double loss = (diff < 0) ? -diff : 0.0;

            avg_gain = (avg_gain * (window_size - 1) + gain) / window_size;
            avg_loss = (avg_loss * (window_size - 1) + loss) / window_size;

            double rolling_rs = (avg_loss == 0.0) ? std::numeric_limits<double>::infinity() : (avg_gain / avg_loss);
            rsi[i - window_size + 1] = 100.0 - (100.0 / (1.0 + rolling_rs));
        }

        return rsi;
    }

    static std::unordered_map<std::string, double> aggregate_features(const std::vector<std::unordered_map<std::string, double> >& data) {
        std::unordered_map<std::string, double> aggregated_features;

        if (data.empty()) {
            return aggregated_features;
        }

        for (std::vector<std::unordered_map<std::string, double> >::const_iterator record_it = data.begin(); record_it != data.end(); ++record_it) {
            for (std::unordered_map<std::string, double>::const_iterator feature_it = record_it->begin(); feature_it != record_it->end(); ++feature_it) {
                aggregated_features[feature_it->first] += feature_it->second;
            }
        }

        for (std::unordered_map<std::string, double>::iterator feature_it = aggregated_features.begin(); feature_it != aggregated_features.end(); ++feature_it) {
            feature_it->second /= data.size();
        }

        return aggregated_features;
    }
};

// Python bindings using pybind11
py::array_t<double> calculate_moving_average_py(py::array_t<double> input, int window_size) {
    py::buffer_info buf = input.request();
    double* ptr = static_cast<double*>(buf.ptr);
    size_t total = buf.size;
    
    std::vector<double> data_vec(ptr, ptr + total);
    std::vector<double> result = FeatureEngineering::calculate_moving_average(data_vec, window_size);
    
    py::array_t<double> output(result.size());
    py::buffer_info output_buf = output.request();
    double* output_ptr = static_cast<double*>(output_buf.ptr);
    std::copy(result.begin(), result.end(), output_ptr);
    
    return output;
}

py::array_t<double> calculate_exponential_moving_average_py(py::array_t<double> input, double alpha) {
    py::buffer_info buf = input.request();
    double* ptr = static_cast<double*>(buf.ptr);
    size_t total = buf.size;
    
    std::vector<double> data_vec(ptr, ptr + total);
    std::vector<double> result = FeatureEngineering::calculate_exponential_moving_average(data_vec, alpha);
    
    py::array_t<double> output(result.size());
    py::buffer_info output_buf = output.request();
    double* output_ptr = static_cast<double*>(output_buf.ptr);
    std::copy(result.begin(), result.end(), output_ptr);
    
    return output;
}

py::array_t<double> calculate_relative_strength_index_py(py::array_t<double> input, int window_size) {
    py::buffer_info buf = input.request();
    double* ptr = static_cast<double*>(buf.ptr);
    size_t total = buf.size;
    
    std::vector<double> data_vec(ptr, ptr + total);
    std::vector<double> result = FeatureEngineering::calculate_relative_strength_index(data_vec, window_size);
    
    py::array_t<double> output(result.size());
    py::buffer_info output_buf = output.request();
    double* output_ptr = static_cast<double*>(output_buf.ptr);
    std::copy(result.begin(), result.end(), output_ptr);
    
    return output;
}

PYBIND11_MODULE(_feature_engineering_cpp, m) {
    m.doc() = "C++ feature engineering module for FraudShield";
    
    m.def("calculate_moving_average", &calculate_moving_average_py,
          "Calculate moving average with specified window size",
          py::arg("input"), py::arg("window_size"));
    
    m.def("calculate_exponential_moving_average", &calculate_exponential_moving_average_py,
          "Calculate exponential moving average with alpha parameter",
          py::arg("input"), py::arg("alpha"));
    
    m.def("calculate_relative_strength_index", &calculate_relative_strength_index_py,
          "Calculate Relative Strength Index (RSI) with specified window size",
          py::arg("input"), py::arg("window_size"));
}

// int main() {
//     // Example usage of FeatureEngineering class
//     double data_arr[] = {1.0, 2.0, 3.0, 4.0, 5.0};
//     std::vector<double> data(data_arr, data_arr + sizeof(data_arr) / sizeof(data_arr[0]));

//     int window_size = 3;
//     std::vector<double> moving_average = FeatureEngineering::calculate_moving_average(data, window_size);
//     std::cout << "Moving Average: ";
//     for (std::vector<double>::iterator it = moving_average.begin(); it != moving_average.end(); ++it) {
//         std::cout << *it << " ";
//     }
//     std::cout << std::endl;

//     double alpha = 0.5;
//     std::vector<double> exponential_moving_average = FeatureEngineering::calculate_exponential_moving_average(data, alpha);
//     std::cout << "Exponential Moving Average: ";
//     for (std::vector<double>::iterator it = exponential_moving_average.begin(); it != exponential_moving_average.end(); ++it) {
//         std::cout << *it << " ";
//     }
//     std::cout << std::endl;

//     std::vector<double> rsi = FeatureEngineering::calculate_relative_strength_index(data, window_size);
//     std::cout << "Relative Strength Index: ";
//     for (std::vector<double>::iterator it = rsi.begin(); it != rsi.end(); ++it) {
//         std::cout << *it << " ";
//     }
//     std::cout << std::endl;

//     std::unordered_map<std::string, double> feature_map1;
//     feature_map1["feature1"] = 1.0;
//     feature_map1["feature2"] = 2.0;

//     std::unordered_map<std::string, double> feature_map2;
//     feature_map2["feature1"] = 3.0;
//     feature_map2["feature2"] = 4.0;

//     std::unordered_map<std::string, double> feature_map3;
//     feature_map3["feature1"] = 5.0;
//     feature_map3["feature2"] = 6.0;

//     std::vector<std::unordered_map<std::string, double> > feature_data;
//     feature_data.push_back(feature_map1);
//     feature_data.push_back(feature_map2);
//     feature_data.push_back(feature_map3);

//     std::unordered_map<std::string, double> aggregated_features = FeatureEngineering::aggregate_features(feature_data);
//     std::cout << "Aggregated Features: " << std::endl;
//     for (std::unordered_map<std::string, double>::iterator it = aggregated_features.begin(); it != aggregated_features.end(); ++it) {
//         std::cout << it->first << ": " << it->second << std::endl;
//     }

//     return 0;
// }
