from __future__ import annotations

import numpy as np
import pandas as pd

from ebike_sim.config import SimulationConfig


class BikePhysicsModel:
    """Berechnet Fahrwiderstände, Antriebskraft und mechanische Leistung."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config

    def calculate(self, route: pd.DataFrame) -> pd.DataFrame:
        """
        Berechnet die auftretenden Kräfte und Leistungen.

        Die Luftdichte wird für jeden Streckenpunkt abhängig von der
        Höhe über dem Meeresspiegel und der Umgebungstemperatur bestimmt.
        """

        df = route.copy()
        cfg = self.config

        mass = cfg.total_mass_kg
        velocity = df["speed_m_s"].to_numpy(dtype=float)
        acceleration = df["acceleration_m_s2"].to_numpy(dtype=float)
        angle = df["slope_angle_rad"].to_numpy(dtype=float)

        altitude = self._get_altitude(df)
        temperature = self._get_temperature(df)

        air_density = self.calculate_air_density(
            altitude_m=altitude,
            temperature_c=temperature,
        )

        force_acceleration = mass * acceleration

        force_grade = (
            mass
            * cfg.gravity_m_s2
            * np.sin(angle)
        )

        force_rolling = (
            cfg.rolling_resistance_coefficient
            * mass
            * cfg.gravity_m_s2
            * np.cos(angle)
        )

        force_aero = (
            0.5
            * air_density
            * cfg.drag_area_m2
            * velocity**2
        )

        total_force = (
            force_acceleration
            + force_grade
            + force_rolling
            + force_aero
        )

        # Negative Kraft bedeutet Bremsen oder Schieben durch Gefälle.
        # Ohne Rekuperation muss der Motor keine negative Leistung liefern.
        if cfg.allow_regeneration:
            drive_force = total_force
        else:
            drive_force = np.maximum(total_force, 0.0)

        mechanical_power_required = drive_force * velocity

        rider_power = np.minimum(
            np.full_like(
                mechanical_power_required,
                cfg.rider_power_w,
            ),
            np.maximum(
                mechanical_power_required,
                0.0,
            ),
        )

        motor_mechanical_power_request = (
            mechanical_power_required
            - rider_power
        )

        df["air_density_kg_m3"] = air_density
        df["force_acceleration_n"] = force_acceleration
        df["force_grade_n"] = force_grade
        df["force_rolling_n"] = force_rolling
        df["force_aero_n"] = force_aero
        df["drive_force_n"] = drive_force
        df["mechanical_power_required_w"] = mechanical_power_required
        df["rider_power_w"] = rider_power
        df["motor_mechanical_power_request_w"] = (
            motor_mechanical_power_request
        )

        return df

    def calculate_air_density(
        self,
        altitude_m: float | np.ndarray,
        temperature_c: float | np.ndarray | None = None,
    ) -> float | np.ndarray:
        """
        Berechnet die Luftdichte aus Höhe und Temperatur.

        Zuerst wird der Luftdruck mit der barometrischen Höhenformel
        bestimmt. Anschließend wird die Luftdichte mit der idealen
        Gasgleichung berechnet.

        Parameters
        ----------
        altitude_m:
            Höhe über dem Meeresspiegel in Metern.

        temperature_c:
            Lufttemperatur in Grad Celsius. Wird kein Wert übergeben,
            wird ambient_temperature_c aus der Konfiguration verwendet.

        Returns
        -------
        float oder numpy.ndarray
            Luftdichte in kg/m³.
        """

        altitude = np.asarray(
            altitude_m,
            dtype=float,
        )

        if temperature_c is None:
            temperature_c = self.config.ambient_temperature_c

        temperature = np.asarray(
            temperature_c,
            dtype=float,
        )

        temperature_k = temperature + 273.15

        if np.any(temperature_k <= 0.0):
            raise ValueError(
                "Die Temperatur muss größer als -273,15 °C sein."
            )

        p0 = self.config.sea_level_pressure_pa
        t0 = self.config.sea_level_temperature_k
        lapse_rate = self.config.temperature_lapse_rate_k_per_m
        gas_constant = self.config.specific_gas_constant_air
        gravity = self.config.gravity_m_s2

        pressure_base = (
            1.0
            - lapse_rate * altitude / t0
        )

        if np.any(pressure_base <= 0.0):
            raise ValueError(
                "Die Höhe liegt außerhalb des gültigen "
                "Bereichs des Atmosphärenmodells."
            )

        exponent = gravity / (
            gas_constant * lapse_rate
        )

        pressure_pa = p0 * np.power(
            pressure_base,
            exponent,
        )

        air_density = pressure_pa / (
            gas_constant * temperature_k
        )

        if air_density.ndim == 0:
            return float(air_density)

        return air_density

    def _get_altitude(self, route: pd.DataFrame) -> np.ndarray:
        """
        Liest die Höhe aus dem Route-DataFrame.

        Es werden mehrere übliche Spaltennamen unterstützt.
        """

        possible_columns = (
            "elevation_m",
            "altitude_m",
            "elevation",
            "altitude",
        )

        for column in possible_columns:
            if column in route.columns:
                altitude = route[column].to_numpy(
                    dtype=float
                )

                if np.isnan(altitude).any():
                    altitude = (
                        pd.Series(altitude)
                        .interpolate()
                        .bfill()
                        .ffill()
                        .to_numpy()
                    )

                return altitude

        raise KeyError(
            "Im Route-DataFrame wurde keine Höhenspalte gefunden. "
            "Erwartet wird eine der Spalten: "
            "'elevation_m', 'altitude_m', "
            "'elevation' oder 'altitude'."
        )

    def _get_temperature(
        self,
        route: pd.DataFrame,
    ) -> float | np.ndarray:
        """
        Verwendet eine Temperaturspalte aus den Routendaten, sofern sie
        vorhanden ist. Ansonsten wird die konstante Temperatur aus der
        Konfiguration verwendet.
        """

        possible_columns = (
            "temperature_c",
            "ambient_temperature_c",
        )

        for column in possible_columns:
            if column in route.columns:
                temperature = route[column].to_numpy(
                    dtype=float
                )

                if np.isnan(temperature).any():
                    temperature = (
                        pd.Series(temperature)
                        .interpolate()
                        .fillna(
                            self.config.ambient_temperature_c
                        )
                        .to_numpy()
                    )

                return temperature

        return self.config.ambient_temperature_c