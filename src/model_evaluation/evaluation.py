# src/model_evaluation/evaluation.py

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

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
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
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
