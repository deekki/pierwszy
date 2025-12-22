import math

from palletizer_core.metrics import (
    compute_edge_buffer_metrics,
    compute_edge_contact_fraction,
    compute_orientation_mix,
)


def test_contact_buffer_metrics_golden_values():
    pattern = [(0.0, 0.0, 100.0, 50.0), (100.0, 0.0, 100.0, 50.0)]
    contact_fraction = compute_edge_contact_fraction(pattern)
    assert math.isclose(contact_fraction, 50.0 / 600.0, rel_tol=1e-6)

    buffer_score, min_clearance = compute_edge_buffer_metrics(
        pattern, 220.0, 120.0, 25.0
    )
    assert buffer_score == 0.0
    assert min_clearance == 0.0

    mix_ratio = compute_orientation_mix(pattern, default_orientation=True)
    assert mix_ratio == 0.0


def test_edge_buffer_metrics_nonzero_clearance():
    pattern = [(10.0, 10.0, 100.0, 50.0)]
    buffer_score, min_clearance = compute_edge_buffer_metrics(
        pattern, 200.0, 100.0, 25.0
    )
    assert math.isclose(buffer_score, 0.4, rel_tol=1e-6)
    assert math.isclose(min_clearance, 10.0, rel_tol=1e-6)
