# src/model_training/tests/test_xgboost.py

import unittest
import numpy as np
from xgboost import XGBoostModel

class TestXGBoostModel(unittest.TestCase):
    def setUp(self):
        self.X = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]])
        self.y = np.array([0, 1, 0, 1])
        self.model = XGBoostModel()

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
            'n_estimators': [50, 100, 200],
            'max_depth': [3, 5, 7],
            'learning_rate': [0.01, 0.1, 0.3]
        }
        best_params, best_score = self.model.hyperparameter_tuning(self.X, self.y, param_grid)
        self.assertIsInstance(best_params, dict)
        self.assertGreaterEqual(best_score, 0.0)

    def test_save_and_load_model(self):
        self.model.train(self.X, self.y)
        filepath = 'xgboost_model.pkl'
        self.model.save_model(filepath)
        loaded_model = XGBoostModel.load_model(filepath)
        self.assertIsInstance(loaded_model, XGBoostModel)


if __name__ == '__main__':
    unittest.main()
