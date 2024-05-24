# src/model_evaluation/tests/test_evaluation.py

import unittest
import numpy as np
import pandas as pd
from evaluation import ModelEvaluation

class TestModelEvaluation(unittest.TestCase):
    def setUp(self):
        self.y_true = np.array([1, 0, 1, 1, 0, 0, 1, 0, 1, 0])
        self.y_pred = np.array([1, 0, 1, 0, 0, 1, 1, 0, 0, 0])
        self.y_prob = np.array([0.8, 0.2, 0.9, 0.6, 0.3, 0.7, 0.8, 0.4, 0.5, 0.2])

    def test_calculate_metrics(self):
        evaluation = ModelEvaluation(self.y_true, self.y_pred, self.y_prob)
        accuracy, precision, recall, f1, auc = evaluation.calculate_metrics()

        self.assertIsInstance(accuracy, float)
        self.assertIsInstance(precision, float)
        self.assertIsInstance(recall, float)
        self.assertIsInstance(f1, float)
        self.assertIsInstance(auc, float)

    def test_plot_confusion_matrix(self):
        evaluation = ModelEvaluation(self.y_true, self.y_pred)
        evaluation.plot_confusion_matrix(normalize=True, save_path='confusion_matrix.png')

    def test_generate_report(self):
        evaluation = ModelEvaluation(self.y_true, self.y_pred, self.y_prob)
        report = evaluation.generate_report(output_path='evaluation_report.csv')

        self.assertIsInstance(report, pd.DataFrame)
        self.assertEqual(report.shape, (5, 2))
        self.assertTrue('Metric' in report.columns)
        self.assertTrue('Value' in report.columns)


if __name__ == '__main__':
    unittest.main()
