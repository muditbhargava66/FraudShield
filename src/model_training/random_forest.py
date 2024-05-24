# src/model_training/random_forest.py

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib

class RandomForestModel:
    def __init__(self, params=None):
        self.model = RandomForestClassifier(**params) if params else RandomForestClassifier()

    def train(self, X, y):
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
        self.model.fit(X_train, y_train)
        y_pred = self.model.predict(X_val)
        accuracy = accuracy_score(y_val, y_pred)
        precision = precision_score(y_val, y_pred)
        recall = recall_score(y_val, y_pred)
        f1 = f1_score(y_val, y_pred)
        return accuracy, precision, recall, f1

    def predict(self, X):
        return self.model.predict(X)

    def hyperparameter_tuning(self, X, y, param_grid):
        grid_search = GridSearchCV(self.model, param_grid, cv=5, scoring='accuracy')
        grid_search.fit(X, y)
        self.model = grid_search.best_estimator_
        return grid_search.best_params_, grid_search.best_score_

    def save_model(self, filepath):
        joblib.dump(self.model, filepath)

    @staticmethod
    def load_model(filepath):
        model = joblib.load(filepath)
        return RandomForestModel(model.get_params())
