"""
Unit tests for provider service.
"""

from maparr.services.providers import builtin_providers, get_provider


def test_builtin_providers_not_empty():
    providers = builtin_providers()
    assert len(providers) > 0
    # Ensure at least OSM standard exists
    ids = [p.id for p in providers]
    assert 'osm-standard' in ids

def test_get_provider_returns_correct():
    osm = get_provider('osm-standard')
    assert osm is not None
    assert osm.name == 'OpenStreetMap (Standard)'
    assert osm.offline_allowed is True
