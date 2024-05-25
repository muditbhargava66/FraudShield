// src/data_cleaning/data_cleaning.cpp

#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <numeric>
#include <cmath>

class DataCleaning {
public:
    static void remove_missing_values(std::vector<double>& data) {
        data.erase(std::remove(data.begin(), data.end(), NAN), data.end());
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
        double sq_sum = 0.0;
        for (std::vector<double>::const_iterator it = data.begin(); it != data.end(); ++it) {
            double diff = *it - mean;
            sq_sum += diff * diff;
        }
        return std::sqrt(sq_sum / data.size());
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
        double mean = calculate_mean(data);
        double stddev = calculate_stddev(data, mean);
        data.erase(std::remove_if(data.begin(), data.end(), OutlierPredicate(mean, stddev, threshold)), data.end());
    }
};

extern "C" {
    void remove_missing_values(double* data, int nrows, int ncols) {
        std::vector<double> data_vec(data, data + nrows * ncols);
        DataCleaning::remove_missing_values(data_vec);
        std::copy(data_vec.begin(), data_vec.end(), data);
    }

    void remove_outliers(double* data, int nrows, int ncols, double threshold) {
        std::vector<double> data_vec(data, data + nrows * ncols);
        DataCleaning::remove_outliers(data_vec, threshold);
        std::copy(data_vec.begin(), data_vec.end(), data);
    }
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
