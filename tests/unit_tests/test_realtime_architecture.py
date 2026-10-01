"""
Unit tests validating Real-time capabilities.
"""

from unittest.mock import MagicMock, patch

from fraudshield.core.risk_engine.engine import HybridRiskEngine


def test_hybrid_risk_engine_weighting():
    """Validates the HybridRiskEngine core logic scaling factors."""
    engine = HybridRiskEngine(ml_weight=0.5, graph_weight=0.3, rule_weight=0.2)

    # Test safe transaction
    res = engine.evaluate_transaction(ml_score=0.1, graph_score=0.0, rules_breached=0, max_rules=5)
    assert res["composite_fraud_score"] == round((0.1 * 0.5) + 0 + 0, 4)
    assert res["assigned_risk_level"] == "LOW"
    assert res["action"] == "ALLOW"

    # Test complete anomaly triggering override
    res_high = engine.evaluate_transaction(ml_score=0.9, graph_score=0.96, rules_breached=5, max_rules=5)
    # 0.96 graph_score is > 0.95 which triggers the override cap natively
    assert res_high["composite_fraud_score"] >= 0.95
    assert res_high["assigned_risk_level"] == "HIGH"
    assert res_high["action"] == "BLOCK"


@patch("fraudshield.ml.explainability.shap_explainer.shap")
def test_shap_explainer_mocked(mock_shap):
    """Verifies SHAP explainer initializes when shap library exists."""
    import pandas as pd

    from fraudshield.ml.explainability.shap_explainer import FraudExplainer

    # Mocking standard SHAP outputs
    mock_explainer_instance = MagicMock()
    # List of lists simulating XGBoost arrays
    mock_explainer_instance.shap_values.return_value = [[0.1, -0.2], [[0.5, 0.3]]]
    mock_shap.TreeExplainer.return_value = mock_explainer_instance

    explainer = FraudExplainer("dummy_model")

    df = pd.DataFrame([{"feat_1": 10, "feat_2": 20}])
    explanation = explainer.explain_transaction(df)

    assert "Error" not in explanation
    assert len(explanation) == 2


def test_shap_explainer_failure():
    import pandas as pd

    from fraudshield.ml.explainability.shap_explainer import FraudExplainer

    explainer = FraudExplainer(None)
    explainer.explainer = None  # Force failure

    df = pd.DataFrame([{"feat_1": 10}])
    res = explainer.explain_transaction(df)
    assert "Error" in res


def test_graph_builder_initialization():
    from fraudshield.graph.graph_builder.builder import FraudGraphBuilder

    builder = FraudGraphBuilder(driver=MagicMock())
    assert builder is not None
    assert builder.driver is not None


def test_risk_engine_with_ring_detector():
    """Verify that the ring detector score is blended into the composite risk."""
    mock_ring_detector = MagicMock()
    mock_ring_detector.assess_account.return_value = 0.9

    engine = HybridRiskEngine(
        ml_weight=0.6,
        graph_weight=0.3,
        rule_weight=0.1,
        ring_detector=mock_ring_detector,
    )

    # With low graph_score (0.1) but high ring_score (0.9), the ring should boost graph
    result = engine.evaluate_transaction(
        ml_score=0.5,
        graph_score=0.1,
        rules_breached=0,
        max_rules=5,
        account_id="acct_123",
    )

    # graph_score should become max(0.1, 0.9) = 0.9
    # composite = 0.5*0.6 + 0.9*0.3 + 0*0.1 = 0.3 + 0.27 + 0 = 0.57
    assert result["graph_contribution"] == 0.9
    assert result["composite_fraud_score"] == 0.57
    mock_ring_detector.assess_account.assert_called_once_with("acct_123")


def test_risk_engine_without_ring_detector():
    """Verify that without a ring detector, graph_score is used as-is."""
    engine = HybridRiskEngine(ml_weight=0.6, graph_weight=0.3, rule_weight=0.1)

    result = engine.evaluate_transaction(
        ml_score=0.5,
        graph_score=0.2,
        rules_breached=0,
        max_rules=5,
        account_id="acct_123",
    )

    # composite = 0.5*0.6 + 0.2*0.3 + 0*0.1 = 0.3 + 0.06 = 0.36
    assert result["graph_contribution"] == 0.2
    assert result["composite_fraud_score"] == 0.36
