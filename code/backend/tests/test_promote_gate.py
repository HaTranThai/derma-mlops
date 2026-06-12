from app.services.mlflow_service import PROMOTE_RULES, evaluate_gate

PROD = {"macro_f1": 0.7145, "melanoma_recall": 0.5806, "accuracy": 0.8410}


def test_weak_candidate_rejected():
    cand = {"macro_f1": 0.33, "melanoma_recall": 0.30, "accuracy": 0.50}
    assert evaluate_gate(PROD, cand, PROMOTE_RULES)["passed"] is False


def test_better_candidate_promoted():
    cand = {"macro_f1": 0.75, "melanoma_recall": 0.62, "accuracy": 0.85}
    assert evaluate_gate(PROD, cand, PROMOTE_RULES)["passed"] is True


def test_accuracy_tolerance_allows_small_drop():
    cand = {"macro_f1": 0.72, "melanoma_recall": 0.59, "accuracy": 0.831}
    assert evaluate_gate(PROD, cand, PROMOTE_RULES)["passed"] is True


def test_accuracy_big_drop_rejected():
    cand = {"macro_f1": 0.72, "melanoma_recall": 0.59, "accuracy": 0.74}
    assert evaluate_gate(PROD, cand, PROMOTE_RULES)["passed"] is False


def test_macro_f1_worse_rejected():
    cand = {"macro_f1": 0.70, "melanoma_recall": 0.62, "accuracy": 0.85}
    assert evaluate_gate(PROD, cand, PROMOTE_RULES)["passed"] is False


def test_checks_cover_all_metrics():
    cand = {"macro_f1": 0.75, "melanoma_recall": 0.62, "accuracy": 0.85}
    metrics = {c["metric"] for c in evaluate_gate(PROD, cand, PROMOTE_RULES)["checks"]}
    assert metrics == {"macro_f1", "melanoma_recall", "accuracy"}


def test_melanoma_absolute_floor_rejects_below_min():
    prod = {"macro_f1": 0.30, "melanoma_recall": 0.35, "accuracy": 0.60}
    cand = {"macro_f1": 0.45, "melanoma_recall": 0.38, "accuracy": 0.62}
    result = evaluate_gate(prod, cand, PROMOTE_RULES)
    assert result["passed"] is False
    assert any(c.get("rule") == "min" and not c["passed"] for c in result["checks"])


def test_macro_f1_margin_rejects_noise_improvement():
    prod = {"macro_f1": 0.50, "melanoma_recall": 0.50, "accuracy": 0.60}
    cand = {"macro_f1": 0.502, "melanoma_recall": 0.51, "accuracy": 0.60}
    assert evaluate_gate(prod, cand, PROMOTE_RULES)["passed"] is False
