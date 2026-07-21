import logging
from pathlib import Path 

import matplotlib.pyplot as plt
import numpy as np

from ebike_sim.config import SimulationConfig
from ebike_sim.gps_reader import GPSDataReader
from ebike_sim.route_analyzer import RouteAnalyzer
from ebike_sim.physics import BikePhysicsModel
from ebike_sim.motor import Motor
from ebike_sim.battery import LiPoBattery, NMCBattery
from ebike_sim.simulation import EBikeSimulation



def run_studies(gps_file: Path) -> None:
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Lese GPS-Daten aus {gps_file}...")
    gps_data = GPSDataReader().read(gps_file)


    # 1. Studie: Einfluss der Gesamtmasse (Fahrer + Rad)
    test_masses = np.arange(70, 135, 5)
    energy_results_mass = []

    print("\nStarte Sarameterstudie 1: Masse...")
    for mass in test_masses:
        config = SimulationConfig(smoothing_enabled=True)
        config.total_mass_kg = float(mass)

        route = RouteAnalyzer(smoothing_enabled = True)
        physics = BikePhysicsModel(config)
        motor = Motor(
            torque_constant_nm_per_a=config.motor_torque_constant_nm_per_a,
            efficiency=config.motor_efficiency,
            max_mechanical_power_w=config.motor_max_mechanical_power_w,
        )

        lipo = LiPoBattery(series_cells=10, parallel_cells=4, cell_capacity_ah=3.0, initial_soc=1.0)
        nmc = NMCBattery(series_cells=10, parallel_cells=4, cell_capacity_ah=3.0, initial_soc=1.0)

        simulation = EBikeSimulation(config, physics, motor)
        results, summary = simulation.run(route, [lipo, nmc])

        lipo_end_soc = results["lipo_soc"].iloc[-1]
        consumed_wh = 444.0 - (lipo_end_soc * 444.0)
        energy_results_mass.append(consumed_wh)
        print(f"- Masse: {mass:3d} kg -> Verbrauch: {consumed_wh:.2f} WH")

        plt.figure(figsize=(8, 5))
        plt.plot(test_masses, energy_results_mass, marker='o', color='blue', linewidth=2)
        plt.title("Parameterstudie: Einfluss der Masse auf den Energieverbrauch")
        plt.xlabel("Gesamtmasse (Fahrer + Fahrrad) / kg")
        plt.ylabel("Verbrauchte Energie (LiPo) / Wh")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / "study_01_mass.png", dpi=160)
        plt.close()


# 2.Studie Einfluss des Luftwiderstandes (cw-Wert)
# hier noch einfügen (Michael)


if __name__ == "__main__":
    # Deaktiviert die Info-Logs
    logging.getLogger("ebike_sim").setLevel(logging.WARNING)

    gps_path = Path("data/final_project_input_data.csv")
    run_studies(gps_path)