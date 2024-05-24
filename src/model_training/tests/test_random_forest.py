# src/model_training/tests/test_random_forest.py

import unittest
import numpy as np
from random_forest import RandomForestModel

class TestRandomForestModel(unittest.TestCase):
    def setUp(self):
        self.X = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]])
        self.y = np.array([0, 1, 0, 1])
        self.model = RandomForestModel()

    def test_train(self):
        accuracy, precision, recall, f1 = self.model.train(self.X, self.y)
        self.assertGreaterEqual(accuracy, 0.0)
        self.assertGreaterEqual(precision, 0.0)
        self.assertGreaterEqual(recall, 0.0)
        self.assertGreaterEqual(f1, 0.0)

    def test_predict(self):
        self.model.train(self.X, self.y)
        y_pred = self.model.predict(self.X)
        self.assertEqual(len(y_pred), len(self.y))

    def test_hyperparameter_tuning(self):
        param_grid = {
            'n_estimators': [10, 50, 100],
            'max_depth': [None, 5, 10],
            'min_samples_split': [2, 5, 10]
        }
        best_params, best_score = self.model.hyperparameter_tuning(self.X, self.y, param_grid)
        self.assertIsInstance(best_params, dict)
        self.assertGreaterEqual(best_score, 0.0)

    def test_save_and_load_model(self):
        self.model.train(self.X, self.y)
        filepath = 'random_forest_model.pkl'
        self.model.save_model(filepath)
        loaded_model = RandomForestModel.load_model(filepath)
        self.assertIsInstance(loaded_model, RandomForestModel)
