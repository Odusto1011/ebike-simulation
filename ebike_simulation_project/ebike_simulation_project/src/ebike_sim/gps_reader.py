from __future__ import annotations

import csv
import logging
from pathlib import Path

import pandas as pd

from .exceptions import GPSDataError

logger = logging.getLogger(__name__)


class GPSDataReader:
    """Liest CSV-GPS-Daten ein und vereinheitlicht die Spaltennamen."""

    COLUMN_ALIASES = {
        "timestamp": {
            "timestamp", "time", "datetime", "date_time", "zeit", "zeitstempel"
        },
        "latitude": {
            "latitude", "lat", "breitengrad", "breite"
        },
        "longitude": {
            "longitude", "lon", "lng", "laengengrad", "längengrad", "laenge", "länge"
        },
        "elevation_m": {
            "elevation", "elevation_m", "altitude", "alt", "height",
            "hoehe", "höhe", "hoehe_m", "höhe_m"
        },
    }

    def __init__(self, delimiter: str | None = None) -> None:
        self.delimiter = delimiter

    def read(self, file_path: Path) -> pd.DataFrame:
        if not file_path.exists():
            raise GPSDataError(f"GPS-Datei wurde nicht gefunden: {file_path}")

        delimiter = self.delimiter or self._detect_delimiter(file_path)
        try:
            df = pd.read_csv(file_path, sep=delimiter)
        except Exception as exc:
            raise GPSDataError(f"CSV-Datei konnte nicht gelesen werden: {exc}") from exc

        df.columns = [str(column).strip().lower() for column in df.columns]
        rename_map = self._build_rename_map(df.columns)
        df = df.rename(columns=rename_map)

        required = {"timestamp", "latitude", "longitude", "elevation_m"}
        missing = required.difference(df.columns)
        if missing:
            raise GPSDataError(
                "Folgende Pflichtspalten fehlen: "
                + ", ".join(sorted(missing))
                + ". Erkannt wurden: "
                + ", ".join(map(str, df.columns))
            )

        df = df[list(required)].copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        for column in ("latitude", "longitude", "elevation_m"):
            df[column] = pd.to_numeric(df[column], errors="coerce")

        invalid_rows = df.isna().any(axis=1)
        if invalid_rows.any():
            logger.warning(
                "%d unvollständige oder ungültige Zeilen werden entfernt.",
                int(invalid_rows.sum()),
            )
            df = df.loc[~invalid_rows].copy()

        if len(df) < 2:
            raise GPSDataError("Mindestens zwei gültige GPS-Messpunkte sind erforderlich.")

        df = df.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)

        if not df["latitude"].between(-90.0, 90.0).all():
            raise GPSDataError("Mindestens ein Breitengrad liegt außerhalb [-90, 90].")
        if not df["longitude"].between(-180.0, 180.0).all():
            raise GPSDataError("Mindestens ein Längengrad liegt außerhalb [-180, 180].")

        if len(df) < 2:
            raise GPSDataError("Nach dem Entfernen doppelter Zeitstempel bleiben zu wenige Daten.")

        logger.info("%d gültige GPS-Messpunkte eingelesen.", len(df))
        return df

    @staticmethod
    def _detect_delimiter(file_path: Path) -> str:
        sample = file_path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
        try:
            return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except csv.Error:
            return ","

    def _build_rename_map(self, columns: pd.Index) -> dict[str, str]:
        rename_map: dict[str, str] = {}
        for target, aliases in self.COLUMN_ALIASES.items():
            matches = [column for column in columns if column in aliases]
            if len(matches) > 1:
                logger.warning(
                    "Mehrere mögliche Spalten für %s gefunden: %s. Verwende %s.",
                    target,
                    matches,
                    matches[0],
                )
            if matches:
                rename_map[matches[0]] = target
        return rename_map
