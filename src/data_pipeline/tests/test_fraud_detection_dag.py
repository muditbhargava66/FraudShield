# src/data_pipeline/tests/test_fraud_detection_dag.py

from airflow.models import DagBag
from datetime import datetime, timedelta
import unittest

class TestFraudDetectionDAG(unittest.TestCase):
    def setUp(self):
        self.dagbag = DagBag()

    def test_dag_loaded(self):
        dag = self.dagbag.get_dag(dag_id='fraud_detection_pipeline')
        self.assertIsNotNone(dag)

    def test_dag_tasks(self):
        dag = self.dagbag.get_dag(dag_id='fraud_detection_pipeline')
        tasks = dag.tasks
        task_ids = list(map(lambda task: task.task_id, tasks))
        expected_task_ids = [
            'data_ingestion',
            'data_preprocessing',
            'model_training',
            'model_evaluation',
            'model_deployment',
        ]
        self.assertListEqual(sorted(task_ids), sorted(expected_task_ids))

    def test_dag_schedule_interval(self):
        dag = self.dagbag.get_dag(dag_id='fraud_detection_pipeline')
        self.assertEqual(dag.schedule_interval, timedelta(days=1))


if __name__ == '__main__':
    unittest.main()
