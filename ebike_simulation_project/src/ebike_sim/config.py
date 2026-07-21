from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    """Zentrale Modellparameter der E-Bike-Simulation."""

    rider_mass_kg: float = 70.0
    bike_mass_kg: float = 10.0

    # Vorgegeben: Produkt aus Luftwiderstandsbeiwert c_w und Stirnfläche A.
    drag_area_m2: float = 0.5625
    air_density_kg_m3: float = 1.225

    wheel_diameter_inch: float = 27.0
    rolling_resistance_coefficient: float = 0.008
    gravity_m_s2: float = 9.80665

    motor_torque_constant_nm_per_a: float = 1.5
    motor_efficiency: float = 0.85
    motor_max_mechanical_power_w: float = 250.0

    # Fahrerleistung kann bei Bedarf verändert werden.
    rider_power_w: float = 0.0

    smoothing_enabled: bool = True
    smoothing_window: int = 5

    max_valid_speed_m_s: float = 25.0
    max_abs_acceleration_m_s2: float = 8.0
    max_abs_grade: float = 0.35

    allow_regeneration: bool = True
    regeneration_efficiency: float = 0.60

    @property
    def total_mass_kg(self) -> float:
        return self.rider_mass_kg + self.bike_mass_kg

    @property
    def wheel_radius_m(self) -> float:
        return self.wheel_diameter_inch * 0.0254 / 2.0
