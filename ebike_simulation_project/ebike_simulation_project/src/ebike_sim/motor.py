from __future__ import annotations

import numpy as np
import pandas as pd


class Motor:
    """Vereinfachtes Modell eines radnahen Motors ohne Getriebe."""

    def __init__(
        self,
        torque_constant_nm_per_a: float,
        efficiency: float,
        max_mechanical_power_w: float,
    ) -> None:
        if torque_constant_nm_per_a <= 0:
            raise ValueError("Die Motorkonstante muss positiv sein.")
        if not 0 < efficiency <= 1:
            raise ValueError("Der Motorwirkungsgrad muss in (0, 1] liegen.")
        if max_mechanical_power_w <= 0:
            raise ValueError("Die maximale Motorleistung muss positiv sein.")

        self.torque_constant_nm_per_a = torque_constant_nm_per_a
        self.efficiency = efficiency
        self.max_mechanical_power_w = max_mechanical_power_w

    def calculate(self, data: pd.DataFrame, wheel_radius_m: float) -> pd.DataFrame:
        df = data.copy()

        requested = df["motor_mechanical_power_request_w"].to_numpy()
        delivered = np.clip(
            requested,
            -self.max_mechanical_power_w,
            self.max_mechanical_power_w,
        )

        velocity = df["speed_m_s"].to_numpy()
        force = np.divide(
            delivered,
            velocity,
            out=np.zeros_like(delivered),
            where=velocity > 0.1,
        )
        torque = force * wheel_radius_m
        motor_current = torque / self.torque_constant_nm_per_a

        electrical_power = np.where(
            delivered >= 0,
            delivered / self.efficiency,
            delivered * self.efficiency,
        )

        df["motor_power_limited"] = np.abs(requested) > self.max_mechanical_power_w
        df["motor_mechanical_power_w"] = delivered
        df["motor_force_n"] = force
        df["motor_torque_nm"] = torque
        df["motor_current_a"] = motor_current
        df["motor_electrical_power_w"] = electrical_power
        return df
