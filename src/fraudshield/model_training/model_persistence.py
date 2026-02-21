"""
FraudShield - Advanced Anomaly Detection Pipeline

This module provides unified access points for securely serializing
and deserializing trained machine learning models onto the file system.

File: model_persistence.py
Author: Mudit Bhargava
License: MIT
"""

import os
import joblib


def save_model(model, model_path):
    """
    Saves a trained model to disk.

    Args:
        model: Trained model object.
        model_path (str): Path to save the model.
    """
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)


def load_model(model_path):
    """
    Loads a trained model from disk.

    Args:
        model_path (str): Path to the saved model.

    Returns:
        Loaded model object.
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    model = joblib.load(model_path)
    return model
