# src/model_persistence/model_persistence.py

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

if __name__ == "__main__":
    # Example usage
    from sklearn.ensemble import RandomForestClassifier

    # Train a sample model
    X_train = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    y_train = [0, 1, 1]
    model = RandomForestClassifier()
    model.fit(X_train, y_train)

    # Save the model
    model_path = "data/models/sample_model.pkl"
    save_model(model, model_path)
    print(f"Model saved to: {model_path}")

    # Load the model
    loaded_model = load_model(model_path)
    print("Model loaded successfully.")