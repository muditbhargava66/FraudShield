# src/model_evaluation/evaluation.py

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import joblib

class ModelEvaluation:
    def __init__(self, y_true, y_pred, y_prob=None):
        self.y_true = y_true
        self.y_pred = y_pred
        self.y_prob = y_prob

    def calculate_metrics(self):
        accuracy = accuracy_score(self.y_true, self.y_pred)
        precision = precision_score(self.y_true, self.y_pred)
        recall = recall_score(self.y_true, self.y_pred)
        f1 = f1_score(self.y_true, self.y_pred)
        if self.y_prob is not None:
            auc = roc_auc_score(self.y_true, self.y_prob)
        else:
            auc = None
        return accuracy, precision, recall, f1, auc

    def plot_confusion_matrix(self, normalize=False, save_path=None):
        cm = confusion_matrix(self.y_true, self.y_pred)
        if normalize:
            cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, cmap='Blues', fmt='.2f' if normalize else 'd', xticklabels=['Negative', 'Positive'], yticklabels=['Negative', 'Positive'])
        plt.xlabel('Predicted Labels')
        plt.ylabel('True Labels')
        plt.title('Confusion Matrix')

        if save_path:
            import os
            plot_dir = 'data/plots/'
            if not os.path.exists(plot_dir):
                os.makedirs(plot_dir)
            plt.savefig(os.path.join(plot_dir, 'confusion_matrix.png'), dpi=300, bbox_inches='tight')
        else:
            plt.show()

    def generate_report(self, output_path=None):
        accuracy, precision, recall, f1, auc = self.calculate_metrics()

        report = pd.DataFrame({
            'Metric': ['Accuracy', 'Precision', 'Recall', 'F1 Score', 'AUC'],
            'Value': [accuracy, precision, recall, f1, auc]
        })

        if output_path:
            report.to_csv(output_path, index=False)
        else:
            print(report)

        return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Evaluate trained models')
    parser.add_argument('--model_path', type=str, default='/Users/mudit/Developer/FraudShield/data/models/xgboost.pkl', help='Path to the trained model file')
    parser.add_argument('--test_data', type=str, default='/Users/mudit/Developer/FraudShield/data/models/test_data.npy', help='Path to the test data NumPy file')
    parser.add_argument('--output_path', type=str, default='/Users/mudit/Developer/FraudShield/data/models/evaluation_report.csv', help='Path to save the evaluation report')
    args = parser.parse_args()

    try:
        # Load the trained model
        model = joblib.load(args.model_path)

        # Load the test data
        test_data = np.load(args.test_data)
        X_test = test_data[:, :-1]
        y_test = test_data[:, -1]

        # Threshold the target variable if it is continuous
        if np.issubdtype(y_test.dtype, np.floating):
            threshold = 0.5
            y_test = (y_test > threshold).astype(int)

        # Predict using the trained model
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else None

        # Evaluate the model
        evaluation = ModelEvaluation(y_test, y_pred, y_prob)
        evaluation.generate_report(args.output_path)

        # Plot confusion matrix
        evaluation.plot_confusion_matrix(save_path='confusion_matrix.png')

    except FileNotFoundError as e:
        print(f"File not found: {str(e)}")
    except Exception as e:
        print(f"Error during model evaluation: {str(e)}")