from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ebike_sim.config import SimulationConfig
from ebike_sim.gps_reader import GPSDataReader
from ebike_sim.route_analyzer import RouteAnalyzer
from ebike_sim.physics import BikePhysicsModel
from ebike_sim.motor import Motor
from ebike_sim.battery import LiPoBattery, NMCBattery
from ebike_sim.simulation import EBikeSimulation
from ebike_sim.visualization import ResultVisualizer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auswertung und Simulation einer E-Bike-Fahrt aus GPS-Daten."
    )
    parser.add_argument("gps_file", type=Path, help="Pfad zur CSV-Datei mit GPS-Daten")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Verzeichnis für Ergebnisse und Diagramme",
    )
    parser.add_argument(
        "--delimiter",
        default=None,
        help="CSV-Trennzeichen. Ohne Angabe wird es automatisch erkannt.",
    )
    parser.add_argument(
        "--no-smoothing",
        action="store_true",
        help="Deaktiviert die Glättung von Geschwindigkeit und Höhe.",
    )
    return parser.parse_args()


def configure_logging(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(output_dir / "simulation.log", encoding="utf-8"),
        ],
    )


def main() -> None:
    args = parse_args()
    configure_logging(args.output_dir)
    logger = logging.getLogger(__name__)

    config = SimulationConfig(smoothing_enabled=not args.no_smoothing)

    logger.info("Lese GPS-Daten aus %s", args.gps_file)
    gps_data = GPSDataReader(delimiter=args.delimiter).read(args.gps_file)

    logger.info("Analysiere Route")
    route = RouteAnalyzer(config).analyze(gps_data)
    print("\n--- GPS Orientierungs-Check ---")
    print(route[["distance_m", "elevation_filtered_m", "heading_deg"]].head(15))
    print("-------------------------------\n")

    physics = BikePhysicsModel(config)
    motor = Motor(
        torque_constant_nm_per_a=config.motor_torque_constant_nm_per_a,
        efficiency=config.motor_efficiency,
        max_mechanical_power_w=config.motor_max_mechanical_power_w,
    )

    # Annahme, weil in der Aufgabenstellung keine Parallelzahl/Zellkapazität angegeben ist:
    # 10S4P mit 3,0 Ah pro Zelle.
    lipo = LiPoBattery(
        series_cells=10,
        parallel_cells=4,
        cell_capacity_ah=3.0,
        initial_soc=1.0,
    )
    nmc = NMCBattery(
        series_cells=10,
        parallel_cells=4,
        cell_capacity_ah=3.0,
        initial_soc=1.0,
    )

    simulation = EBikeSimulation(config, physics, motor)
    results, summary = simulation.run(route, [lipo, nmc])

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results_path = args.output_dir / "simulation_results.csv"
    results.to_csv(results_path, index=False)

    summary_path = args.output_dir / "summary.txt"
    summary_path.write_text(summary.to_text(), encoding="utf-8")

    ResultVisualizer().create_all(results, args.output_dir)

    print(summary.to_text())
    print(f"\nErgebnisse: {results_path}")
    print(f"Diagramme: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
