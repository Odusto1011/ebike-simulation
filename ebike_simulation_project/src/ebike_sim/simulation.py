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
    """Zusammenfassung der wichtigsten Simulationsergebnisse."""

    total_distance_km: float
    duration_min: float
    average_speed_km_h: float
    ascent_m: float
    descent_m: float

    max_required_power_w: float
    max_motor_power_w: float
    motor_power_limit_count: int

    average_air_density_kg_m3: float
    minimum_air_density_kg_m3: float
    maximum_air_density_kg_m3: float

    final_soc_percent: dict[str, float]
    consumed_energy_wh: dict[str, float]

    def to_text(self) -> str:
        """Gibt die Simulationsergebnisse als formatierten Text zurück."""

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
            "",
            "--- Luftdichte ---",
            (
                "Mittlere Luftdichte:     "
                f"{self.average_air_density_kg_m3:.4f} kg/m³"
            ),
            (
                "Minimale Luftdichte:     "
                f"{self.minimum_air_density_kg_m3:.4f} kg/m³"
            ),
            (
                "Maximale Luftdichte:     "
                f"{self.maximum_air_density_kg_m3:.4f} kg/m³"
            ),
        ]

        for name, soc_percent in self.final_soc_percent.items():
            energy_wh = self.consumed_energy_wh[name]

            lines.append(
                f"{name:>4} End-SOC:             "
                f"{soc_percent:.2f} % "
                f"(Verbrauch {energy_wh:.2f} Wh)"
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
        """Führt die vollständige E-Bike-Simulation aus."""

        if route.empty:
            raise ValueError(
                "Die Simulation kann nicht mit einer leeren Route "
                "ausgeführt werden."
            )

        if not batteries:
            raise ValueError(
                "Für die Simulation muss mindestens ein Akku "
                "übergeben werden."
            )

        df = self.physics.calculate(route)

        required_physics_columns = {
            "air_density_kg_m3",
            "force_aero_n",
            "mechanical_power_required_w",
            "motor_mechanical_power_request_w",
        }

        missing_columns = required_physics_columns.difference(df.columns)

        if missing_columns:
            missing_text = ", ".join(sorted(missing_columns))

            raise KeyError(
                "Das Physikmodell hat nicht alle benötigten "
                f"Ergebnisspalten erzeugt. Fehlend: {missing_text}"
            )

        # Motorberechnung
        df = self.motor.calculate(
            df,
            self.config.wheel_radius_m,
        )

        # Batteriesimulation
        for battery in batteries:
            soc_values: list[float] = []
            ocv_values: list[float] = []
            terminal_voltage_values: list[float] = []
            current_values: list[float] = []
            energy_values: list[float] = []
            power_limit_values: list[bool] = []
            temp_values: list[float] = []
            brake_power_values: list[float] = []

            cumulative_energy_wh = 0.0

            for row in df.itertuples(index=False):
                electrical_power_w = float(
                    row.motor_electrical_power_w
                )

                if electrical_power_w < 0.0:
                    if self.config.allow_regeneration:
                        electrical_power_w *= (
                            self.config.regeneration_efficiency
                        )
                    else:
                        electrical_power_w = 0.0

                delta_t_s = float(row.delta_t_s)

                if not np.isfinite(delta_t_s) or delta_t_s < 0.0:
                    delta_t_s = 0.0

                step = battery.step(
                    electrical_power_w,
                    delta_t_s,
                )

                cumulative_energy_wh += step.energy_delta_wh

                soc_values.append(step.soc)
                ocv_values.append(step.open_circuit_voltage_v)
                terminal_voltage_values.append(
                    step.terminal_voltage_v
                )
                current_values.append(step.battery_current_a)
                energy_values.append(cumulative_energy_wh)
                power_limit_values.append(step.power_limited)

                temp_values.append(step.temperatur_c)
                brake_power_values.append(step.brake_dissipated_power_w)

            battery_key = battery.name.lower()

            df[f"{battery_key}_soc"] = soc_values
            df[f"{battery_key}_ocv_v"] = ocv_values
            df[f"{battery_key}_terminal_voltage_v"] = (
                terminal_voltage_values
            )
            df[f"{battery_key}_battery_current_a"] = current_values
            df[f"{battery_key}_energy_consumed_wh"] = energy_values
            df[f"{battery_key}_power_limited"] = power_limit_values

            df[f"{battery_key}_temperatur_c"] = temp_values
            df[f"{battery_key}_brake_dissipated_power_w"] = brake_power_values

            logger.info(
                "%s-Simulation beendet: SOC %.2f %%, Energie %.2f Wh",
                battery.name,
                battery.soc * 100.0,
                cumulative_energy_wh,
            )

        duration_s = float(df["elapsed_s"].iloc[-1])
        total_distance_m = float(df["distance_m"].iloc[-1])

        if duration_s > 0.0:
            average_speed_m_s = total_distance_m / duration_s
        else:
            average_speed_m_s = 0.0

        air_density = df["air_density_kg_m3"].to_numpy(dtype=float)

        if not np.all(np.isfinite(air_density)):
            raise ValueError(
                "Die berechnete Luftdichte enthält ungültige Werte."
            )

        final_soc_percent = {
            battery.name: float(
                df[f"{battery.name.lower()}_soc"].iloc[-1] * 100.0
            )
            for battery in batteries
        }

        consumed_energy_wh = {
            battery.name: float(
                df[
                    f"{battery.name.lower()}_energy_consumed_wh"
                ].iloc[-1]
            )
            for battery in batteries
        }

        summary = SimulationSummary(
            total_distance_km=total_distance_m / 1000.0,
            duration_min=duration_s / 60.0,
            average_speed_km_h=average_speed_m_s * 3.6,
            ascent_m=float(df["ascent_m"].sum()),
            descent_m=float(df["descent_m"].sum()),
            max_required_power_w=float(
                df["mechanical_power_required_w"].max()
            ),
            max_motor_power_w=float(
                df["motor_mechanical_power_w"].max()
            ),
            motor_power_limit_count=int(
                df["motor_power_limited"].sum()
            ),
            average_air_density_kg_m3=float(
                np.mean(air_density)
            ),
            minimum_air_density_kg_m3=float(
                np.min(air_density)
            ),
            maximum_air_density_kg_m3=float(
                np.max(air_density)
            ),
            final_soc_percent=final_soc_percent,
            consumed_energy_wh=consumed_energy_wh,
        )

        return df, summary