// src/feature_engineering/tests/feature_engineering_test.cpp

#include <gtest/gtest.h>
#include "feature_engineering.cpp"

TEST(FeatureEngineeringTest, CalculateMovingAverage) {
    std::vector<double> data = { 1.0, 2.0, 3.0, 4.0, 5.0 };
    std::vector<double> expected = { 2.0, 3.0, 4.0 };
    int window_size = 3;
    std::vector<double> result = FeatureEngineering::calculate_moving_average(data, window_size);
    EXPECT_EQ(result, expected);
}

TEST(FeatureEngineeringTest, CalculateExponentialMovingAverage) {
    std::vector<double> data = { 1.0, 2.0, 3.0, 4.0, 5.0 };
    std::vector<double> expected = { 1.0, 1.5, 2.25, 3.125, 4.0625 };
    double alpha = 0.5;
    std::vector<double> result = FeatureEngineering::calculate_exponential_moving_average(data, alpha);
    for (size_t i = 0; i < result.size(); ++i) {
        EXPECT_NEAR(result[i], expected[i], 1e-6);
    }
}

TEST(FeatureEngineeringTest, CalculateRelativeStrengthIndex) {
    std::vector<double> data = { 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0 };
    std::vector<double> expected = { 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0 };
    int window_size = 3;
    std::vector<double> result = FeatureEngineering::calculate_relative_strength_index(data, window_size);
    for (size_t i = 0; i < result.size(); ++i) {
        EXPECT_NEAR(result[i], expected[i], 1e-6);
    }
}

TEST(FeatureEngineeringTest, AggregateFeatures) {
    std::vector<std::unordered_map<std::string, double>> data = {
        {{"feature1", 1.0}, {"feature2", 2.0}},
        {{"feature1", 3.0}, {"feature2", 4.0}},
        {{"feature1", 5.0}, {"feature2", 6.0}}
    };
    std::unordered_map<std::string, double> expected = {
        {"feature1", 3.0},
        {"feature2", 4.0}
    };
    std::unordered_map<std::string, double> result = FeatureEngineering::aggregate_features(data);
    EXPECT_EQ(result, expected);
}

int main(int argc, char** argv) {
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
