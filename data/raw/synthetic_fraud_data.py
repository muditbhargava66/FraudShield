from sklearn.datasets import make_classification
import pandas as pd

# Generate synthetic data
X, y = make_classification(n_samples=1000, n_features=10, n_informative=5, n_redundant=2, n_classes=2, random_state=42)

# Save the synthetic data as a CSV file
data = pd.DataFrame(X, columns=[f'feature_{i}' for i in range(X.shape[1])])
data['target'] = y
data.to_csv('data/raw/synthetic_fraud_data.csv', index=False)