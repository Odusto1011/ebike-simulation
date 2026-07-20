from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .config import SimulationConfig
from .exceptions import GPSDataError

logger = logging.getLogger(__name__)


class RouteAnalyzer:
    """Berechnet kinematische Größen aus GPS-Daten."""

    EARTH_RADIUS_M = 6_371_000.0

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config

    def analyze(self, gps: pd.DataFrame) -> pd.DataFrame:
        df = gps.copy()

        df["elapsed_s"] = (
            df["timestamp"] - df["timestamp"].iloc[0]
        ).dt.total_seconds()
        df["delta_t_s"] = df["timestamp"].diff().dt.total_seconds()

        if (df["delta_t_s"].dropna() <= 0).any():
            raise GPSDataError("Zeitstempel müssen streng ansteigend sein.")

        df["segment_distance_m"] = self._haversine_segments(
            df["latitude"].to_numpy(),
            df["longitude"].to_numpy(),
        )
        df["distance_m"] = df["segment_distance_m"].cumsum()

        raw_speed = df["segment_distance_m"] / df["delta_t_s"]
        raw_speed.iloc[0] = 0.0
        raw_speed = raw_speed.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        invalid_speed = raw_speed > self.config.max_valid_speed_m_s
        if invalid_speed.any():
            logger.warning(
                "%d unrealistische Geschwindigkeitswerte wurden begrenzt.",
                int(invalid_speed.sum()),
            )
        raw_speed = raw_speed.clip(0.0, self.config.max_valid_speed_m_s)

        elevation = df["elevation_m"].astype(float)
        if self.config.smoothing_enabled:
            window = max(3, int(self.config.smoothing_window))
            elevation = elevation.rolling(window, center=True, min_periods=1).median()
            speed = raw_speed.rolling(window, center=True, min_periods=1).mean()
        else:
            speed = raw_speed

        df["elevation_filtered_m"] = elevation
        df["speed_m_s"] = speed
        df["speed_km_h"] = speed * 3.6

        acceleration = df["speed_m_s"].diff() / df["delta_t_s"]
        acceleration.iloc[0] = 0.0
        acceleration = acceleration.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        df["acceleration_m_s2"] = acceleration.clip(
            -self.config.max_abs_acceleration_m_s2,
            self.config.max_abs_acceleration_m_s2,
        )

        df["delta_h_m"] = df["elevation_filtered_m"].diff().fillna(0.0)
        horizontal_distance = np.sqrt(
            np.maximum(
                df["segment_distance_m"].to_numpy() ** 2
                - df["delta_h_m"].to_numpy() ** 2,
                0.0,
            )
        )
        grade = np.divide(
            df["delta_h_m"].to_numpy(),
            horizontal_distance,
            out=np.zeros(len(df), dtype=float),
            where=horizontal_distance > 0.5,
        )
        df["grade"] = np.clip(
            grade,
            -self.config.max_abs_grade,
            self.config.max_abs_grade,
        )
        df["slope_angle_rad"] = np.arctan(df["grade"])
        df["grade_percent"] = df["grade"] * 100.0

        df["ascent_m"] = df["delta_h_m"].clip(lower=0.0)
        df["descent_m"] = -df["delta_h_m"].clip(upper=0.0)

        return df

    @classmethod
    def _haversine_segments(
        cls, latitude_deg: np.ndarray, longitude_deg: np.ndarray
    ) -> np.ndarray:
        lat = np.radians(latitude_deg)
        lon = np.radians(longitude_deg)

        dlat = np.diff(lat, prepend=lat[0])
        dlon = np.diff(lon, prepend=lon[0])

        a = (
            np.sin(dlat / 2.0) ** 2
            + np.cos(np.roll(lat, 1))
            * np.cos(lat)
            * np.sin(dlon / 2.0) ** 2
        )
        a[0] = 0.0
        c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(np.maximum(1.0 - a, 0.0)))
        return cls.EARTH_RADIUS_M * c
