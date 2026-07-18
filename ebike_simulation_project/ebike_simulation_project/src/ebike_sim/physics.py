from __future__ import annotations

import numpy as np
import pandas as pd

from config import SimulationConfig


class BikePhysicsModel:
    """Berechnet Fahrwiderstände, Antriebskraft und mechanische Leistung."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config

    def calculate(self, route: pd.DataFrame) -> pd.DataFrame:
        df = route.copy()
        cfg = self.config

        mass = cfg.total_mass_kg
        velocity = df["speed_m_s"].to_numpy()
        acceleration = df["acceleration_m_s2"].to_numpy()
        angle = df["slope_angle_rad"].to_numpy()

        force_acceleration = mass * acceleration
        force_grade = mass * cfg.gravity_m_s2 * np.sin(angle)
        force_rolling = (
            cfg.rolling_resistance_coefficient
            * mass
            * cfg.gravity_m_s2
            * np.cos(angle)
        )
        force_aero = (
            0.5
            * cfg.air_density_kg_m3
            * cfg.drag_area_m2
            * velocity**2
        )

        total_force = (
            force_acceleration + force_grade + force_rolling + force_aero
        )

        # Negative Kraft bedeutet Bremsen/Schieben durch Gefälle. Ohne
        # Rekuperation muss der Motor dafür keine negative Leistung liefern.
        if cfg.allow_regeneration:
            drive_force = total_force
        else:
            drive_force = np.maximum(total_force, 0.0)

        mechanical_power_required = drive_force * velocity
        rider_power = np.minimum(
            np.full_like(mechanical_power_required, cfg.rider_power_w),
            np.maximum(mechanical_power_required, 0.0),
        )
        motor_mechanical_power_request = mechanical_power_required - rider_power

        df["force_acceleration_n"] = force_acceleration
        df["force_grade_n"] = force_grade
        df["force_rolling_n"] = force_rolling
        df["force_aero_n"] = force_aero
        df["drive_force_n"] = drive_force
        df["mechanical_power_required_w"] = mechanical_power_required
        df["rider_power_w"] = rider_power
        df["motor_mechanical_power_request_w"] = motor_mechanical_power_request
        return df
