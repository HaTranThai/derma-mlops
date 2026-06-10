from app.repositories.monitoring_repository import _proportions, _psi, _psi_level


def test_proportions_normalize_to_one():
    rows = [{"predicted_class": "nv", "count": 7}, {"predicted_class": "mel", "count": 3}]
    props = _proportions(rows, {"nv", "mel"})
    assert abs(props["nv"] - 0.7) < 1e-9
    assert abs(props["mel"] - 0.3) < 1e-9


def test_proportions_missing_class_is_zero():
    rows = [{"predicted_class": "nv", "count": 10}]
    props = _proportions(rows, {"nv", "mel"})
    assert props["mel"] == 0.0


def test_identical_distributions_zero_psi():
    dist = {"nv": 0.7, "mel": 0.3}
    assert _psi(dist, dist) < 1e-6


def test_shifted_distribution_high_psi():
    baseline = {"nv": 0.9, "mel": 0.1}
    recent = {"nv": 0.1, "mel": 0.9}
    assert _psi(recent, baseline) > 0.25


def test_psi_levels():
    assert _psi_level(0.05) == "none"
    assert _psi_level(0.15) == "moderate"
    assert _psi_level(0.40) == "significant"
