# src/model_training/train_models.py

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import LabelEncoder
import argparse
import logging
import joblib

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def train_random_forest(X_train, y_train):
    """
    Train a Random Forest classifier.
    
    Args:
        X_train (numpy.ndarray): Training features.
        y_train (numpy.ndarray): Training labels.
    
    Returns:
        RandomForestClassifier: Trained Random Forest classifier.
    """
    rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_model.fit(X_train, y_train)
    return rf_model

def train_xgboost(X_train, y_train):
    """
    Train an XGBoost classifier.
    
    Args:
        X_train (numpy.ndarray): Training features.
        y_train (numpy.ndarray): Training labels.
    
    Returns:
        XGBClassifier: Trained XGBoost classifier.
    """
    xgb_model = XGBClassifier(n_estimators=100, random_state=42)
    xgb_model.fit(X_train, y_train)
    return xgb_model

def evaluate_model(model, X_test, y_test):
    """
    Evaluate the trained model on the test set.
    
    Args:
        model: Trained classifier model.
        X_test (numpy.ndarray): Test features.
        y_test (numpy.ndarray): Test labels.
    
    Returns:
        dict: Dictionary containing evaluation metrics.
    """
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1
    }

def save_model(model, model_path):
    """
    Save the trained model to disk.
    
    Args:
        model: Trained classifier model.
        model_path (str): Path to save the model.
    """
    joblib.dump(model, model_path)
    logger.info(f"Model saved to: {model_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Train fraud detection models')
    parser.add_argument('--preprocessed_data', type=str, default='/Users/mudit/Developer/FraudShield/data/models/preprocessed_data.npy', help='Path to the preprocessed data NumPy file')
    parser.add_argument('--output_dir', type=str, default='/Users/mudit/Developer/FraudShield/data/models/', help='Directory to save the trained models')
    args = parser.parse_args()

    try:
        # Load the preprocessed data
        preprocessed_data = np.load(args.preprocessed_data)
        X = preprocessed_data[:, :-1]
        y = preprocessed_data[:, -1]
        
        # Encode the target variable
        label_encoder = LabelEncoder()
        y = label_encoder.fit_transform(y)

        # Split the data into train and test sets
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Train and evaluate Random Forest model
        rf_model = train_random_forest(X_train, y_train)
        rf_metrics = evaluate_model(rf_model, X_test, y_test)
        logger.info("Random Forest Metrics:")
        logger.info(rf_metrics)
        save_model(rf_model, args.output_dir + 'random_forest.pkl')

        # Train and evaluate XGBoost model
        xgb_model = train_xgboost(X_train, y_train)
        xgb_metrics = evaluate_model(xgb_model, X_test, y_test)
        logger.info("XGBoost Metrics:")
        logger.info(xgb_metrics)
        save_model(xgb_model, args.output_dir + 'xgboost.pkl')

    except FileNotFoundError as e:
        logger.error(f"Preprocessed data file not found: {str(e)}")
    except Exception as e:
        logger.error(f"Error during model training: {str(e)}")