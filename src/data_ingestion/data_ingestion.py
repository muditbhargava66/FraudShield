import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
import argparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def preprocess_data(data):
    """
    Preprocesses the input data by performing scaling, one-hot encoding, and imputation.
    
    Args:
        data (pandas.DataFrame): DataFrame containing the input data.
    
    Returns:
        pandas.DataFrame: Preprocessed data as a DataFrame.
    """
    try:
        # Validate input data
        if not isinstance(data, pd.DataFrame):
            raise ValueError("Input data must be a pandas DataFrame")
        
        # Handle missing values
        data.dropna(inplace=True)
        
        # Remove outliers
        # You can use techniques like Z-score or Interquartile Range (IQR) to identify and remove outliers
        # For simplicity, let's assume there are no outliers in this example
        
        numeric_features = data.select_dtypes(include=['int64', 'float64']).columns
        categorical_features = data.select_dtypes(include=['object']).columns

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
            ])

        preprocessed_data = preprocessor.fit_transform(data)
        preprocessed_columns = numeric_features.tolist() + list(preprocessor.named_transformers_['cat'].named_steps['onehot'].get_feature_names(categorical_features))
        preprocessed_df = pd.DataFrame(preprocessed_data, columns=preprocessed_columns)
        
        # Feature engineering
        # Calculate moving average
        preprocessed_df['moving_average'] = preprocessed_df[numeric_features].rolling(window=3).mean()
        
        # Calculate exponential moving average
        preprocessed_df['exponential_moving_average'] = preprocessed_df[numeric_features].ewm(alpha=0.5).mean()
        
        return preprocessed_df

    except Exception as e:
        logger.error(f"Error during data preprocessing: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Preprocess data for fraud detection')
    parser.add_argument('--input_data', type=str, default='/Users/mudit/Developer/FraudShield/data/processed/ingested_data.csv', help='Path to the input data CSV file')
    parser.add_argument('--output_data', type=str, default='/Users/mudit/Developer/FraudShield/data/models/preprocessed_data.npy', help='Path to save the preprocessed data as a NumPy file')
    args = parser.parse_args()

    try:
        ingested_data = pd.read_csv(args.input_data)
        preprocessed_data = preprocess_data(ingested_data)
        
        # Save the preprocessed data as a NumPy file
        np.save(args.output_data, preprocessed_data.values)
        
        logger.info(f"Preprocessed data saved to: {args.output_data}")
    except FileNotFoundError as e:
        logger.error(f"Input data file not found: {str(e)}")
    except Exception as e:
        logger.error(f"Error during data preprocessing: {str(e)}")