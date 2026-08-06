"""
Simple tests for geocoder service.
"""

from maparr.services.geocoder import get_geocoder

def test_geocoder_search_returns_results():
    geocoder = get_geocoder()
    results = geocoder.search('London', limit=5)
    assert isinstance(results, list)
    # Should have at least one result (London, UK)
    assert len(results) > 0
    first = results[0]
    assert 'name' in first
    assert 'lat' in first
    assert 'lon' in first

def test_geocoder_reverse_returns_location():
    geocoder = get_geocoder()
    # Coordinates for Greenwich, London
    results = geocoder.reverse(51.4769, -0.0005, max_distance_km=10, limit=1)
    assert isinstance(results, list)
    if len(results) > 0:
        res = results[0]
        assert 'name' in res