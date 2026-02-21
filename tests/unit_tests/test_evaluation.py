import unittest
import numpy as np
import pandas as pd
import tempfile
from pathlib import Path
from fraudshield.model_evaluation.evaluation import ModelEvaluation


class TestModelEvaluation(unittest.TestCase):
    def setUp(self):
        self.y_true = np.array([1, 0, 1, 1, 0, 0, 1, 0, 1, 0])
        self.y_pred = np.array([1, 0, 1, 0, 0, 1, 1, 0, 0, 0])
        self.y_prob = np.array([0.8, 0.2, 0.9, 0.6, 0.3, 0.7, 0.8, 0.4, 0.5, 0.2])

    def test_calculate_metrics(self):
        evaluation = ModelEvaluation(self.y_true, self.y_pred, self.y_prob)
        accuracy, precision, recall, f1, auc, ap = evaluation.calculate_metrics()

        self.assertIsInstance(accuracy, float)
        self.assertIsInstance(precision, float)
        self.assertIsInstance(recall, float)
        self.assertIsInstance(f1, float)
        self.assertIsInstance(auc, float)
        self.assertIsInstance(ap, float)

    def test_plot_confusion_matrix(self):
        evaluation = ModelEvaluation(self.y_true, self.y_pred)
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "confusion_matrix.png"
            evaluation.plot_confusion_matrix(normalize=True, save_path=save_path)

    def test_generate_report(self):
        evaluation = ModelEvaluation(self.y_true, self.y_pred, self.y_prob)
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "evaluation_report.csv"
            report = evaluation.generate_report(output_path=report_path)

        self.assertIsInstance(report, pd.DataFrame)
        self.assertEqual(report.shape, (6, 2))
        self.assertTrue("Metric" in report.columns)
        self.assertTrue("Value" in report.columns)


if __name__ == "__main__":
    unittest.main()
