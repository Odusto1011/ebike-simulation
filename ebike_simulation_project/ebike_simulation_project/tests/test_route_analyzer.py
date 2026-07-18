import pandas as pd
import pytest

from ebike_sim.config import SimulationConfig
from ebike_sim.route_analyzer import RouteAnalyzer


def test_route_distance_is_positive() -> None:
    gps = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2026-01-01T10:00:00Z", "2026-01-01T10:00:10Z"]
            ),
            "latitude": [47.0, 47.0001],
            "longitude": [11.0, 11.0],
            "elevation_m": [500.0, 501.0],
        }
    )
    result = RouteAnalyzer(SimulationConfig(smoothing_enabled=False)).analyze(gps)
    assert result["distance_m"].iloc[-1] > 0
    assert result["speed_m_s"].iloc[-1] > 0
