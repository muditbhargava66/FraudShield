import pytest

pytest.importorskip("airflow")

from fraudshield.data_pipeline.airflow_dags import fraud_detection_dag


def _dag():
    return fraud_detection_dag.dag


def test_dag_loaded():
    dag = _dag()
    assert dag is not None
    assert dag.dag_id == "fraud_detection_pipeline"


def test_dag_tasks():
    dag = _dag()
    task_ids = [task.task_id for task in dag.tasks]
    assert sorted(task_ids) == sorted(["data_ingestion", "data_preprocessing", "model_training", "model_evaluation", "model_deployment"])


def test_dag_schedule_interval():
    from datetime import timedelta

    dag = _dag()
    schedule = getattr(dag, "schedule", None)
    if schedule is not None:
        assert schedule == timedelta(days=1)
    else:
        assert dag.schedule_interval == timedelta(days=1)
