# src/data_preprocessing/data_preprocessing.py

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
import argparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def preprocess_data(data, test_size=0.2):
    """
    Preprocesses the input data by performing scaling, one-hot encoding, and imputation.
    
    Args:
        data (pandas.DataFrame): DataFrame containing the input data.
        test_size (float): Fraction of data to be used for testing.
    
    Returns:
        tuple: Preprocessed train and test data as DataFrames.
    """
    try:
        logger.info("Starting data preprocessing...")
        
        # Validate input data
        if not isinstance(data, pd.DataFrame):
            logger.error("Input data must be a pandas DataFrame")
            raise ValueError("Input data must be a pandas DataFrame")
        
        # Handle missing values
        logger.info("Handling missing values...")
        numeric_features = data.select_dtypes(include=['int64', 'float64']).columns
        data[numeric_features] = data[numeric_features].fillna(data[numeric_features].mean())
        
        # Separate numeric and categorical features
        logger.info("Separating numeric and categorical features...")
        categorical_features = data.select_dtypes(include=['object']).columns.tolist()
        
        # Scale numeric features
        logger.info("Scaling numeric features...")
        scaler = StandardScaler()
        data[numeric_features] = scaler.fit_transform(data[numeric_features])

        # One-hot encode categorical features
        logger.info("One-hot encoding categorical features...")
        encoder = OneHotEncoder(handle_unknown='ignore')
        encoded_features = encoder.fit_transform(data[categorical_features]).toarray()
        encoded_columns = encoder.get_feature_names_out(categorical_features)
        encoded_df = pd.DataFrame(encoded_features, columns=encoded_columns)

        # Combine numeric and encoded categorical features
        logger.info("Combining numeric and encoded categorical features...")
        preprocessed_data = pd.concat([data[numeric_features], encoded_df], axis=1)
        
        # Feature engineering
        logger.info("Performing feature engineering...")
        
        # Calculate moving average
        logger.info("Calculating moving average...")
        preprocessed_data['moving_average'] = preprocessed_data[numeric_features].rolling(window=3).mean().mean(axis=1)
        
        # Calculate exponential moving average
        logger.info("Calculating exponential moving average...")
        preprocessed_data['exponential_moving_average'] = preprocessed_data[numeric_features].ewm(alpha=0.5).mean().mean(axis=1)
        
        # Split the data into train and test sets
        logger.info(f"Splitting data into train and test sets with test size: {test_size}...")
        train_data, test_data = train_test_split(preprocessed_data, test_size=test_size, random_state=42, stratify=data['fraud'])
        
        # Add the target variable to the train and test data
        train_data['fraud'] = data['fraud']
        test_data['fraud'] = data['fraud']
        
        logger.info("Data preprocessing completed successfully!")
        return train_data, test_data

    except Exception as e:
        logger.error(f"Error during data preprocessing: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Preprocess data for fraud detection')
    parser.add_argument('--input_data', type=str, default='/Users/mudit/Developer/FraudShield/data/processed/ingested_data.csv', help='Path to the input data CSV file')
    parser.add_argument('--train_data', type=str, default='/Users/mudit/Developer/FraudShield/data/models/preprocessed_data.npy', help='Path to save the preprocessed train data as a NumPy file')
    parser.add_argument('--test_data', type=str, default='/Users/mudit/Developer/FraudShield/data/models/test_data.npy', help='Path to save the preprocessed test data as a NumPy file')
    args = parser.parse_args()

    try:
        logger.info(f"Reading input data from: {args.input_data}")
        ingested_data = pd.read_csv(args.input_data)
        train_data, test_data = preprocess_data(ingested_data)
        
        logger.info(f"Saving preprocessed train data to: {args.train_data}")
        np.save(args.train_data, train_data.values)
        
        logger.info(f"Saving preprocessed test data to: {args.test_data}")
        np.save(args.test_data, test_data.values)
        
        logger.info("Preprocessed data saved successfully!")
    except FileNotFoundError as e:
        logger.error(f"Input data file not found: {str(e)}")
    except Exception as e:
        logger.error(f"Error during data preprocessing: {str(e)}")