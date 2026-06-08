from app.repositories.monitoring_repository import _psi, _psi_level


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
