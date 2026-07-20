from __future__ import annotations

from dataclasses import dataclass
import logging

import numpy as np
import pandas as pd

from .battery import Battery
from .config import SimulationConfig
from .motor import Motor
from .physics import BikePhysicsModel

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SimulationSummary:
    total_distance_km: float
    duration_min: float
    average_speed_km_h: float
    ascent_m: float
    descent_m: float
    max_required_power_w: float
    max_motor_power_w: float
    motor_power_limit_count: int
    final_soc_percent: dict[str, float]
    consumed_energy_wh: dict[str, float]

    def to_text(self) -> str:
        lines = [
            "=== Zusammenfassung der E-Bike-Simulation ===",
            f"Strecke:                 {self.total_distance_km:.2f} km",
            f"Fahrtdauer:              {self.duration_min:.2f} min",
            f"Durchschnitt:            {self.average_speed_km_h:.2f} km/h",
            f"Höhenmeter Anstieg:      {self.ascent_m:.1f} m",
            f"Höhenmeter Abstieg:      {self.descent_m:.1f} m",
            f"Max. benötigte Leistung: {self.max_required_power_w:.1f} W",
            f"Max. Motorleistung:      {self.max_motor_power_w:.1f} W",
            f"Motorbegrenzungen:       {self.motor_power_limit_count}",
        ]
        for name in self.final_soc_percent:
            lines.append(
                f"{name:>4} End-SOC:             "
                f"{self.final_soc_percent[name]:.2f} % "
                f"(Verbrauch {self.consumed_energy_wh[name]:.2f} Wh)"
            )
        return "\n".join(lines)


class EBikeSimulation:
    """Orchestriert Routen-, Physik-, Motor- und Akkumodell."""

    def __init__(
        self,
        config: SimulationConfig,
        physics: BikePhysicsModel,
        motor: Motor,
    ) -> None:
        self.config = config
        self.physics = physics
        self.motor = motor

    def run(
        self,
        route: pd.DataFrame,
        batteries: list[Battery],
    ) -> tuple[pd.DataFrame, SimulationSummary]:
        df = self.physics.calculate(route)
        df = self.motor.calculate(df, self.config.wheel_radius_m)

        for battery in batteries:
            soc_values: list[float] = []
            ocv_values: list[float] = []
            voltage_values: list[float] = []
            current_values: list[float] = []
            energy_values: list[float] = []
            limit_values: list[bool] = []

            cumulative_energy_wh = 0.0
            for row in df.itertuples(index=False):
                power = float(row.motor_electrical_power_w)
                if power < 0 and not self.config.allow_regeneration:
                    power = 0.0
                elif power < 0:
                    power *= self.config.regeneration_efficiency

                step = battery.step(power, float(row.delta_t_s) if not np.isnan(row.delta_t_s) else 0.0)
                cumulative_energy_wh += step.energy_delta_wh

                soc_values.append(step.soc)
                ocv_values.append(step.open_circuit_voltage_v)
                voltage_values.append(step.terminal_voltage_v)
                current_values.append(step.battery_current_a)
                energy_values.append(cumulative_energy_wh)
                limit_values.append(step.power_limited)

            key = battery.name.lower()
            df[f"{key}_soc"] = soc_values
            df[f"{key}_ocv_v"] = ocv_values
            df[f"{key}_terminal_voltage_v"] = voltage_values
            df[f"{key}_battery_current_a"] = current_values
            df[f"{key}_energy_consumed_wh"] = energy_values
            df[f"{key}_power_limited"] = limit_values

            logger.info(
                "%s-Simulation beendet: SOC %.2f %%, Energie %.2f Wh",
                battery.name,
                battery.soc * 100.0,
                cumulative_energy_wh,
            )

        duration_s = float(df["elapsed_s"].iloc[-1])
        total_distance_m = float(df["distance_m"].iloc[-1])
        average_speed_m_s = total_distance_m / duration_s if duration_s > 0 else 0.0

        summary = SimulationSummary(
            total_distance_km=total_distance_m / 1000.0,
            duration_min=duration_s / 60.0,
            average_speed_km_h=average_speed_m_s * 3.6,
            ascent_m=float(df["ascent_m"].sum()),
            descent_m=float(df["descent_m"].sum()),
            max_required_power_w=float(df["mechanical_power_required_w"].max()),
            max_motor_power_w=float(df["motor_mechanical_power_w"].max()),
            motor_power_limit_count=int(df["motor_power_limited"].sum()),
            final_soc_percent={
                battery.name: float(df[f"{battery.name.lower()}_soc"].iloc[-1] * 100.0)
                for battery in batteries
            },
            consumed_energy_wh={
                battery.name: float(df[f"{battery.name.lower()}_energy_consumed_wh"].iloc[-1])
                for battery in batteries
            },
        )
        return df, summary
