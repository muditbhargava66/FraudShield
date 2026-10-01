"""Tests for the API's hybrid assessment and metrics integration."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from fraudshield.ml.inference.api import create_app


@patch("fraudshield.ml.inference.api.FraudGraphBuilder")
def test_predict_uses_hybrid_risk_and_exposes_metrics(mock_graph_builder):
    graph = MagicMock()
    graph.ring_detector = None
    graph.graph_risk.return_value = 0.96
    mock_graph_builder.return_value = graph

    app = create_app()
    with TestClient(app) as client:
        prediction = client.post(
            "/predict",
            json={
                "transaction_id": "api-hybrid-1",
                "account_id": "account-1",
                "amount": 4000.0,
                "is_online": False,
            },
        )
        metrics = client.get("/metrics")

    assert prediction.status_code == 200
    assert prediction.json()["risk_level"] == "HIGH"
    assert prediction.json()["action"] == "BLOCK"
    assert graph.add_transaction.call_count == 1
    assert metrics.status_code == 200
    assert "fraudshield_transactions_total" in metrics.text


@patch("fraudshield.ml.inference.api.FraudGraphBuilder")
def test_predict_rejects_caller_supplied_fraud_label(mock_graph_builder):
    graph = MagicMock()
    graph.ring_detector = None
    mock_graph_builder.return_value = graph

    with TestClient(create_app()) as client:
        response = client.post("/predict", json={"amount": 20.0, "known_fraud": 1})

    assert response.status_code == 422


@patch("fraudshield.ml.inference.api.FraudGraphBuilder")
def test_predict_returns_explanation_for_loaded_model(mock_graph_builder):
    graph = MagicMock()
    graph.ring_detector = None
    mock_graph_builder.return_value = graph

    with TestClient(create_app()) as client:
        response = client.post(
            "/predict",
            json={
                "transaction_id": "explain-1",
                "account_id": "account-1",
                "amount": 4500.0,
                "is_international": True,
                "is_online": False,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert "explanation" in body
    if body["model_loaded"]:
        # Top SHAP factors, sorted by absolute contribution, capped at 5.
        assert isinstance(body["explanation"], dict)
        assert 0 < len(body["explanation"]) <= 5
        assert all(isinstance(value, (int, float)) for value in body["explanation"].values())
    else:
        assert body["explanation"] is None
