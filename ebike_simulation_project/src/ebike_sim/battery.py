from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from .exceptions import BatteryPowerError


@dataclass(slots=True)
class BatteryStep:
    soc: float
    open_circuit_voltage_v: float
    terminal_voltage_v: float
    battery_current_a: float
    power_w: float
    energy_delta_wh: float
    power_limited: bool
    temperatur_c: float


class Battery(ABC):
    """Abstrakte Basisklasse für einen 10SxP-Akku."""

    SOC_POINTS = np.array(
        [0.00, 0.04, 0.09, 0.13, 0.17, 0.21, 0.26, 0.30, 0.40, 0.52, 0.64, 0.76, 0.88, 1.00],
        dtype=float,
    )

    def __init__(
        self,
        name: str,
        series_cells: int,
        parallel_cells: int,
        cell_capacity_ah: float,
        cell_internal_resistance_ohm: float,
        initial_soc: float = 1.0,
        initial_temp_c: float = 1.0,
        ambient_temp_c: float = 20.0,
        thermal_capacity_j_per_k: float = 20.0,
        cooling_coefficient: float = 5.0,
    ) -> None:
        
        if series_cells <= 0 or parallel_cells <= 0:
            raise ValueError("Serien- und Parallelzahl müssen positiv sein.")
        if cell_capacity_ah <= 0:
            raise ValueError("Die Zellkapazität muss positiv sein.")
        if cell_internal_resistance_ohm <= 0:
            raise ValueError("Der Innenwiderstand muss positiv sein.")

        self.name = name
        self.series_cells = series_cells
        self.parallel_cells = parallel_cells
        self.cell_capacity_ah = cell_capacity_ah
        self.cell_internal_resistance_ohm = cell_internal_resistance_ohm
        self.soc = float(np.clip(initial_soc, 0.0, 1.0))

        self.current_temp_c = initial_temp_c
        self.ambient_temp_c = ambient_temp_c
        self.thermal_capacity = thermal_capacity_j_per_k
        self.cooling_coefficient = cooling_coefficient
        

    @property
    def pack_capacity_ah(self) -> float:
        return self.parallel_cells * self.cell_capacity_ah

    @property
    def pack_internal_resistance_ohm(self) -> float:
        # Serienwiderstände addieren sich; Parallelschaltung reduziert Widerstand.
        base_resistance = (
            self.series_cells
            * self.cell_internal_resistance_ohm
            / self.parallel_cells
        )
        
        temp_factor = float(np.exp(-0.04 * (self.current_temp_c - 20.0)))
        return max(base_resistance * temp_factor, base_resistance * 0.3)


    @property
    def nominal_energy_wh(self) -> float:
        return 3.7 * self.series_cells * self.pack_capacity_ah

    @abstractmethod
    def pack_ocv_v(self, soc: float) -> float:
        """Open-Circuit-Spannung des gesamten Packs."""

    def step(self, requested_power_w: float, delta_t_s: float) -> BatteryStep:
        if delta_t_s < 0:
            raise ValueError("delta_t_s darf nicht negativ sein.")

        ocv = self.pack_ocv_v(self.soc)
        resistance = self.pack_internal_resistance_ohm
        power = float(requested_power_w)
        power_limited = False

        if abs(power) < 1e-12 or delta_t_s == 0:
            cooling_w = (self.current_temp_c - self.ambient_temp_c) * self.cooling_coefficient
            self.current_temp_c -= (cooling_w * delta_t_s) /self.thermal_capacity
            return BatteryStep(
                soc=self.soc,
                open_circuit_voltage_v=ocv,
                terminal_voltage_v=ocv,
                battery_current_a=0.0,
                power_w=0.0,
                energy_delta_wh=0.0,
                power_limited=False,
                temperatur_c=float(self.current_temp_c),
            )

        if power > 0:
            # P = (U_oc - I*R)*I. Reale Lösung nur bis U_oc²/(4R).
            max_power = ocv**2 / (4.0 * resistance)
            if power > max_power:
                power = max_power
                power_limited = True

            discriminant = max(ocv**2 - 4.0 * resistance * power, 0.0)
            current = (ocv - np.sqrt(discriminant)) / (2.0 * resistance)
            terminal_voltage = ocv - current * resistance
        else:
            # Laden: P ist negativ, Strom ebenfalls negativ.
            discriminant = ocv**2 - 4.0 * resistance * power
            if discriminant < 0:
                raise BatteryPowerError("Ungültiger Arbeitspunkt beim Laden.")
            current = (ocv - np.sqrt(discriminant)) / (2.0 * resistance)
            terminal_voltage = ocv - current * resistance

        heat_generated_w = (current ** 2) * resistance
        cooling_w = (self.current_temp_c - self.ambient_temp_c) * self.cooling_coefficient
        delta_temp = ((heat_generated_w - cooling_w) * delta_t_s) / self.thermal_capacity
        self.current_temp_c += delta_temp

        # Coulomb Counting. Bei Entladung ist current > 0.
        delta_ah = current * delta_t_s / 3600.0
        new_soc = self.soc - delta_ah / self.pack_capacity_ah

        if new_soc < 0.0:
            # Restenergie wird nur bis SOC=0 entnommen.
            available_ah = self.soc * self.pack_capacity_ah
            current = available_ah * 3600.0 / delta_t_s
            terminal_voltage = max(ocv - current * resistance, 0.0)
            power = terminal_voltage * current
            delta_ah = available_ah
            new_soc = 0.0
            power_limited = True
        elif new_soc > 1.0:
            new_soc = 1.0
            power_limited = True

        self.soc = float(np.clip(new_soc, 0.0, 1.0))
        energy_delta_wh = terminal_voltage * current * delta_t_s / 3600.0

        return BatteryStep(
            soc=self.soc,
            open_circuit_voltage_v=float(ocv),
            terminal_voltage_v=float(terminal_voltage),
            battery_current_a=float(current),
            power_w=float(power),
            energy_delta_wh=float(energy_delta_wh),
            power_limited=power_limited,
            temperatur_c=float(self.current_temp_c),
        )


class LiPoBattery(Battery):
    """LiPo-Pack mit der vorgegebenen OCV-SOC-Kennlinie."""

    PACK_OCV_POINTS_V = np.array(
        [32.00, 35.87, 36.85, 37.56, 37.87, 38.28, 38.81, 39.05, 39.55, 40.27, 40.70, 41.16, 41.65, 42.00],
        dtype=float,
    )

    def __init__(
        self,
        series_cells: int = 10,
        parallel_cells: int = 4,
        cell_capacity_ah: float = 3.0,
        initial_soc: float = 1.0,
        initial_temp_c: float = 20.0,
        ambient_temp_c: float = 20.0,
    ) -> None:
        super().__init__(
            name="LiPo",
            series_cells=series_cells,
            parallel_cells=parallel_cells,
            cell_capacity_ah=cell_capacity_ah,
            cell_internal_resistance_ohm=0.008,
            initial_soc=initial_soc,
            initial_temp_c=initial_temp_c,
            ambient_temp_c=ambient_temp_c,
        )

    def pack_ocv_v(self, soc: float) -> float:
        # Kennlinie wurde für ein 10S-Pack vorgegeben; Skalierung erlaubt andere S-Zahlen.
        base_10s = float(np.interp(np.clip(soc, 0.0, 1.0), self.SOC_POINTS, self.PACK_OCV_POINTS_V))
        return base_10s * self.series_cells / 10.0


class NMCBattery(Battery):
    """NMC-Pack mit der vorgegebenen OCV-SOC-Kennlinie."""

    PACK_OCV_POINTS_V = np.array(
        [32.00, 32.61, 33.17, 33.85, 34.24, 34.66, 35.39, 35.65, 36.65, 37.64, 38.91, 40.14, 41.08, 42.00],
        dtype=float,
    )

    def __init__(
        self,
        series_cells: int = 10,
        parallel_cells: int = 4,
        cell_capacity_ah: float = 3.0,
        initial_soc: float = 1.0,
    ) -> None:
        super().__init__(
            name="NMC",
            series_cells=series_cells,
            parallel_cells=parallel_cells,
            cell_capacity_ah=cell_capacity_ah,
            cell_internal_resistance_ohm=0.007,
            initial_soc=initial_soc,
        )

    def pack_ocv_v(self, soc: float) -> float:
        base_10s = float(np.interp(np.clip(soc, 0.0, 1.0), self.SOC_POINTS, self.PACK_OCV_POINTS_V))
        return base_10s * self.series_cells / 10.0
