# src/data_preprocessing/data_preprocessing.py

import pandas as pd
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
import ctypes
import argparse
import numpy as np

# Load the C++ shared libraries
feature_engineering_lib = ctypes.CDLL("src/feature_engineering/feature_engineering.so")
data_cleaning_lib = ctypes.CDLL("src/data_cleaning/data_cleaning.so")

def preprocess_data(data):
    """
    Preprocesses the input data by performing scaling, one-hot encoding, and imputation.
    
    Args:
        data (pandas.DataFrame): DataFrame containing the input data.
    
    Returns:
        pandas.DataFrame: Preprocessed data as a DataFrame.
    """
    # Convert DataFrame to C++ compatible format
    data_ptr = data.values.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    nrows = data.shape[0]
    ncols = data.shape[1]

    # Clean the data using the C++ data cleaning module
    data_cleaning_lib.remove_missing_values(data_ptr, nrows, ncols)
    data_cleaning_lib.remove_outliers(data_ptr, nrows, ncols, ctypes.c_double(2.0))  # Specify the threshold value

    # Convert the cleaned data back to a DataFrame
    cleaned_data = pd.DataFrame(
        [[data_ptr[i * ncols + j] for j in range(ncols)] for i in range(nrows)],
        columns=data.columns
    )

    numeric_features = cleaned_data.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = cleaned_data.select_dtypes(include=['object']).columns

    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])

    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features)
        ]
    )

    preprocessor.fit(cleaned_data)  # Fit the preprocessor to the data

    preprocessed_data = preprocessor.transform(cleaned_data)

    onehot_encoder = preprocessor.named_transformers_['cat'].named_steps['onehot']
    onehot_encoder.fit(cleaned_data[categorical_features])

    preprocessed_columns = numeric_features.tolist() + list(onehot_encoder.get_feature_names_out(categorical_features))
    preprocessed_df = pd.DataFrame(preprocessed_data, columns=preprocessed_columns)

    # Apply feature engineering using the C++ feature engineering module
    preprocessed_data_ptr = preprocessed_df.values.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    preprocessed_nrows = preprocessed_df.shape[0]
    preprocessed_ncols = preprocessed_df.shape[1]

    feature_engineering_lib.calculate_moving_average(preprocessed_data_ptr, preprocessed_nrows, preprocessed_ncols, ctypes.c_int(3))  # Specify the window size
    feature_engineering_lib.calculate_exponential_moving_average(preprocessed_data_ptr, preprocessed_nrows, preprocessed_ncols, ctypes.c_double(0.5))  # Specify the alpha value

    # Convert the feature-engineered data back to a DataFrame
    feature_engineered_data = pd.DataFrame(
        [[preprocessed_data_ptr[i * preprocessed_ncols + j] for j in range(preprocessed_ncols)] for i in range(preprocessed_nrows)],
        columns=preprocessed_df.columns
    )

    return feature_engineered_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Preprocess data for fraud detection')
    parser.add_argument('--input_data', type=str, default='/Users/mudit/Developer/FraudShield/data/processed/ingested_data.csv', help='Path to the input data CSV file')
    parser.add_argument('--output_data', type=str, default='/Users/mudit/Developer/FraudShield/data/models/preprocessed_data.npy', help='Path to save the preprocessed data as a NumPy file')
    args = parser.parse_args()

    ingested_data = pd.read_csv(args.input_data)
    preprocessed_data = preprocess_data(ingested_data)
    
    # Save the preprocessed data as a NumPy file
    np.save(args.output_data, preprocessed_data.values)
    
    print(f"Preprocessed data saved to: {args.output_data}")