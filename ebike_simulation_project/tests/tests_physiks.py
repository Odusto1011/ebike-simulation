import pytest

from ebike_sim.config import SimulationConfig
from ebike_sim.physics import BikePhysicsModel


def test_air_density_at_sea_level():
    config = SimulationConfig(
        ambient_temperature_c=15.0
    )

    physics = BikePhysicsModel(config)

    density = physics.calculate_air_density(
        altitude_m=0.0
    )

    assert density == pytest.approx(
        1.225,
        rel=0.02,
    )


def test_air_density_decreases_with_altitude():
    config = SimulationConfig(
        ambient_temperature_c=15.0
    )

    physics = BikePhysicsModel(config)

    density_low = physics.calculate_air_density(
        altitude_m=0.0
    )

    density_high = physics.calculate_air_density(
        altitude_m=2000.0
    )

    assert density_high < density_low


def test_air_density_decreases_with_temperature():
    config = SimulationConfig()
    physics = BikePhysicsModel(config)

    density_cold = physics.calculate_air_density(
        altitude_m=500.0,
        temperature_c=0.0,
    )

    density_warm = physics.calculate_air_density(
        altitude_m=500.0,
        temperature_c=30.0,
    )

    assert density_warm < density_cold