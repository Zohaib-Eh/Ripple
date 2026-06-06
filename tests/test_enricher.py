import pytest
import cudf
from impact.enricher import compute_impact

def make_test_data():
    affected_nodes = cudf.DataFrame({
        "node": [10, 11, 12],
        "distance": [0, 1, 2]
    })
    stops = cudf.DataFrame({
        "stop_id": ["S1", "S2", "S3"],
        "node_id": [10, 11, 99],  # S3 not in affected
        "lsoa_code": ["E01000001", "E01000002", "E01000003"],
        "daily_boardings": [500, 300, 200]
    })
    demographics = cudf.DataFrame({
        "lsoa_code": ["E01000001", "E01000002", "E01000003"],
        "population": [2000, 1500, 1000],
        "imd_decile": [3, 7, 5]
    })
    businesses = cudf.DataFrame({
        "borough": ["City of London", "Hackney"],
        "business_count": [8000, 3000]
    })
    return affected_nodes, stops, demographics, businesses

def test_compute_impact_journeys():
    affected, stops, demographics, businesses = make_test_data()
    result = compute_impact(affected, stops, demographics, businesses)
    # S1 (500) + S2 (300) affected; S3 not in affected nodes
    assert result["journeys_affected"] == 800

def test_compute_impact_population():
    affected, stops, demographics, businesses = make_test_data()
    result = compute_impact(affected, stops, demographics, businesses)
    assert result["population_impacted"] == 3500

def test_compute_impact_imd():
    affected, stops, demographics, businesses = make_test_data()
    result = compute_impact(affected, stops, demographics, businesses)
    # Weighted average: (2000*3 + 1500*7) / 3500 = (6000 + 10500) / 3500 = 4.71
    assert abs(result["avg_imd_decile"] - 4.71) < 0.1

def test_compute_impact_returns_all_keys():
    affected, stops, demographics, businesses = make_test_data()
    result = compute_impact(affected, stops, demographics, businesses)
    assert all(k in result for k in ["journeys_affected", "population_impacted", "avg_imd_decile", "businesses_in_zone"])
