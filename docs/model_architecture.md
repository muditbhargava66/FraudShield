# Model Architecture

FraudShield employs state-of-the-art machine learning models to detect and prevent fraudulent activities. The primary models used in the pipeline are Random Forest and XGBoost.

## Random Forest
Random Forest is an ensemble learning method that combines multiple decision trees to make predictions. It is known for its ability to handle high-dimensional data, capture complex interactions, and provide robust results.

The Random Forest model in FraudShield is configured with the following hyperparameters:
- `n_estimators`: The number of decision trees in the forest.
- `max_depth`: The maximum depth of each decision tree.
- `min_samples_split`: The minimum number of samples required to split an internal node.
- `min_samples_leaf`: The minimum number of samples required to be at a leaf node.
- `max_features`: The number of features to consider when looking for the best split.

The optimal values for these hyperparameters are determined through a grid search and cross-validation process to maximize the model's performance.

## XGBoost
XGBoost (Extreme Gradient Boosting) is a powerful gradient boosting framework that combines multiple weak learners to create a strong predictive model. It is known for its excellent performance, scalability, and ability to handle sparse data.

The XGBoost model in FraudShield is configured with the following hyperparameters:
- `n_estimators`: The number of boosting rounds.
- `max_depth`: The maximum depth of each decision tree.
- `learning_rate`: The step size shrinkage used in each boosting round to prevent overfitting.
- `subsample`: The fraction of samples to be used for fitting the individual base learners.
- `colsample_bytree`: The fraction of columns to be randomly sampled for each tree.

Similar to Random Forest, the optimal values for these hyperparameters are determined through a grid search and cross-validation process.

## Model Training and Evaluation
The Random Forest and XGBoost models are trained using the engineered features and the labeled transaction data. The training process involves the following steps:

1. Data Splitting: 
   - When temporal features are present, time-based splitting is enforced to prevent temporal leakage
   - Otherwise, stratified sampling is used to ensure balanced class representation
   - Test size defaults to 20% of the data

2. Label Encoding:
   - String labels are automatically detected and encoded using LabelEncoder
   - The encoder is saved for consistent transformation of test data
   - Validation ensures test data uses the same encoding scheme

3. Model Initialization: 
   - Random Forest: Uses `class_weight='balanced_subsample'` by default, 300 estimators
   - XGBoost: Automatically calculates `scale_pos_weight` based on class imbalance, uses 'aucpr' eval metric

4. Model Training: 
   - Models are trained on the training set using the engineered features as input
   - Predictions are cached to avoid redundant computation during evaluation

5. Model Evaluation: 
   - Trained models are evaluated using accuracy, precision, recall, F1 score, ROC AUC, and Average Precision
   - All metrics use `zero_division=0` to handle edge cases gracefully
   - Confusion matrices are generated and saved as visualizations

6. Hyperparameter Tuning: 
   - Hyperparameters can be provided as JSON strings or dictionaries
   - Separate parameters for Random Forest ('rf') and XGBoost ('xgb')
   - Grid search and cross-validation can be used for optimization

7. Model Selection: 
   - Both models are evaluated and their metrics are saved to `training_metrics.json`
   - The best-performing model is selected based on the evaluation metrics
   - Models are serialized using joblib for deployment

## Model Deployment
The selected model (either Random Forest or XGBoost) is deployed in a production environment for real-time fraud detection. The deployment process involves the following steps:

1. Model Serialization: The trained model is serialized and saved to a file for easy deployment and reuse.

2. API Development: An API is developed to expose the model's predictions to other systems or applications.

3. Integration: The API is integrated with the existing fraud detection system to enable seamless communication and data flow.

4. Monitoring: The deployed model is continuously monitored for performance, drift, and anomalies to ensure its effectiveness and reliability.

The FraudShield pipeline provides a robust and scalable architecture for training, evaluating, and deploying machine learning models for fraud detection. The combination of Random Forest and XGBoost models ensures high accuracy and adaptability to various types of fraudulent patterns.

---