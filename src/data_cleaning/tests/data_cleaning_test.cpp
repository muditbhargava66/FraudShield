
// src/data_cleaning/tests/data_cleaning_test.cpp

#include <gtest/gtest.h>
#include "data_cleaning.cpp"

TEST(DataCleaningTest, RemoveMissingValues) {
    std::vector<double> data = { 1.0, 2.0, NAN, 3.0, NAN, 4.0 };
    DataCleaning::remove_missing_values(data);
    std::vector<double> expected = { 1.0, 2.0, 3.0, 4.0 };
    EXPECT_EQ(data, expected);
}

TEST(DataCleaningTest, RemoveOutliers) {
    std::vector<double> data = { 1.0, 2.0, 3.0, 4.0, 100.0 };
    DataCleaning::remove_outliers(data, 2.0);
    std::vector<double> expected = { 1.0, 2.0, 3.0, 4.0 };
    EXPECT_EQ(data, expected);
}

TEST(DataCleaningTest, CalculateMean) {
    std::vector<double> data = { 1.0, 2.0, 3.0, 4.0 };
    double mean = DataCleaning::calculate_mean(data);
    EXPECT_DOUBLE_EQ(mean, 2.5);
}

TEST(DataCleaningTest, CalculateStdDev) {
    std::vector<double> data = { 1.0, 2.0, 3.0, 4.0 };
    double mean = 2.5;
    double stddev = DataCleaning::calculate_stddev(data, mean);
    EXPECT_DOUBLE_EQ(stddev, 1.118033988749895);
}

int main(int argc, char** argv) {
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
