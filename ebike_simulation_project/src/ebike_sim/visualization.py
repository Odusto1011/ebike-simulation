from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import folium


class ResultVisualizer:
    """Erzeugt die geforderten Diagramme als PNG-Dateien."""

    def create_all(self, data: pd.DataFrame, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)

        self._line_plot(
            data["elapsed_s"] / 60.0,
            [data["speed_km_h"]],
            ["Geschwindigkeit"],
            "Zeit / min",
            "Geschwindigkeit / km/h",
            "Geschwindigkeit über der Zeit",
            output_dir / "01_geschwindigkeit.png",
        )
        self._line_plot(
            data["elapsed_s"] / 60.0,
            [data["acceleration_m_s2"]],
            ["Beschleunigung"],
            "Zeit / min",
            "Beschleunigung / m/s²",
            "Beschleunigung über der Zeit",
            output_dir / "02_beschleunigung.png",
        )
        self._line_plot(
            data["distance_m"] / 1000.0,
            [data["elevation_filtered_m"]],
            ["Höhe"],
            "Strecke / km",
            "Höhe / m",
            "Höhenprofil",
            output_dir / "03_hoehenprofil.png",
        )
        self._line_plot(
            data["elapsed_s"] / 60.0,
            [
                data["mechanical_power_required_w"],
                data["motor_mechanical_power_w"],
            ],
            ["Benötigte Leistung", "Motorleistung"],
            "Zeit / min",
            "Leistung / W",
            "Leistung über der Zeit",
            output_dir / "04_leistung.png",
        )
        self._line_plot(
            data["elapsed_s"] / 60.0,
            [data["motor_torque_nm"]],
            ["Motordrehmoment"],
            "Zeit / min",
            "Drehmoment / Nm",
            "Drehmoment am Motor",
            output_dir / "05_drehmoment.png",
        )
        self._line_plot(
            data["elapsed_s"] / 60.0,
            [
                data["motor_current_a"],
                data["lipo_battery_current_a"],
                data["nmc_battery_current_a"]
            ],
            ["Motorstrom", "Batteriestrom (LiPo)", "Batteriestrom (NMC)"],
            "Zeit / min",
            "Strom / A",
            "Motor- und Batteriestrom",
            output_dir / "06_motorstrom.png",
        )
        self._line_plot(
            data["elapsed_s"] / 60.0,
            [data["lipo_soc"] * 100.0, data["nmc_soc"] * 100.0],
            ["LiPo", "NMC"],
            "Zeit / min",
            "Ladezustand / %",
            "Ladezustand der Akkus",
            output_dir / "07_ladezustand.png",
        )
        self._line_plot(
            data["elapsed_s"] / 60.0,
            [
                data["lipo_terminal_voltage_v"],
                data["nmc_terminal_voltage_v"],
            ],
            ["LiPo", "NMC"],
            "Zeit / min",
            "Klemmenspannung / V",
            "Akkuspannung unter Last",
            output_dir / "08_akkuspannung.png",
        )

        self._line_plot(
            data["elapsed_s"] / 60.0,
            [
                data["lipo_temperatur_c"],
                data["nmc_temperatur_c"],
            ],
            ["LiPo", "NMC"],
            "Zeit / min",
            "Temperatur / °C",
            "Zelltemperatur über der Zeit",
            output_dir / "10_akkutemperatur.png",
        )
        self._line_plot(
            data["elapsed_s"] / 60.0,
            [
                data["lipo_brake_dissipated_power_w"],
                data["nmc_brake_dissipated_power_w"],
            ],
            ["LiPo", "NMC"],
            "Zeit / min",
            "Leistung / W",
            "Im Bremswiderstand dissipierte Leistung",
            output_dir / "11_bremswiderstand.png",
        )
        self._line_plot(
            data["elapsed_s"] / 60.0,
            [data["motor_mechanical_power_w"]],
            ["Motorleistung"],
            "Zeit / min",
            "Leistung / W",
            "Motorleistung über der Zeit",
            output_dir / "12_motorleistung.png",
        )

        self._create_map(data, output_dir / "09_route_map.html")

    @staticmethod
    def _line_plot(
        x: pd.Series,
        ys: list[pd.Series],
        labels: list[str],
        xlabel: str,
        ylabel: str,
        title: str,
        file_path: Path,
    ) -> None:
        plt.figure(figsize=(10, 6))

        min_val = min(y.min() for y in ys)
        if min_val < 0:
            plt.axhline(0, color='black', linestyle='--', linewidth=1, alpha=0.7)

        for y, label in zip(ys, labels):
            plt.plot(x, y, label=label)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title)
        if len(labels) > 1:
            plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(file_path, dpi=160)
        plt.close()
    
    @staticmethod
    def _create_map(data: pd.DataFrame, file_path: Path) -> None:
        if "latitude" not in data.columns or "longitude" not in data.columns:
            return
        
        center_lat = data["latitude"].mean()
        center_lon = data["longitude"].mean()
        route_map = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles="CartoDB positron")

        coordinates = list(zip(data["latitude"], data["longitude"]))

        folium.PolyLine(
            locations=coordinates,
            weight = 5,
            color="blue",
            opacity = 0.8,
            tooltip= "Fahrtroute"
        ).add_to(route_map)


        folium.Marker(coordinates[0], popup="Start", icon=folium.Icon(color="green")).add_to(route_map)
        folium.Marker(coordinates[-1], popup="Ziel", icon=folium.Icon(color="red")).add_to(route_map)
        
        route_map.save(str(file_path))
