"""
Test for estimator service.
"""

from maparr.services.estimator import estimate_download


def test_estimate_returns_positive():
    # Small bbox: 1 degree square approx 111km x 111km at equator
    bbox = [0, 0, 1, 1]
    est = estimate_download(bbox, 0, 1, 10000)  # 10k bytes per tile
    assert est['tiles'] > 0
    assert est['bytes_estimate'] > 0
    assert est['human_size'].endswith('B') or 'KiB' in est['human_size'] or 'MiB' in est['human_size']
