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

    print("\nStarte Sarameterstudie 1: Veränderung der Masse auf den Akkuverbauch:")
    for mass in test_masses:
        config = SimulationConfig(
            smoothing_enabled=True,
            rider_mass_kg=float(mass) - 25.0
        )

        route = RouteAnalyzer(config).analyze(gps_data)
        physics = BikePhysicsModel(config)
        motor = Motor(
            torque_constant_nm_per_a=config.motor_torque_constant_nm_per_a,
            efficiency=config.motor_efficiency,
            max_mechanical_power_w=config.motor_max_mechanical_power_w,
        )

        lipo = LiPoBattery(series_cells=10, parallel_cells=20, cell_capacity_ah=3.0, initial_soc=1.0)
        nmc = NMCBattery(series_cells=10, parallel_cells=4, cell_capacity_ah=3.0, initial_soc=1.0)

        simulation = EBikeSimulation(config, physics, motor)
        results, summary = simulation.run(route, [lipo, nmc])

        lipo_end_soc = results["lipo_soc"].iloc[-1]
        consumed_wh = 2220.0 - (lipo_end_soc * 2220.0)
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
    

        # 2. Studie: Einfluss des Luftwiderstandes (c_w · A)
    test_drag_areas = np.arange(0.30, 0.86, 0.05)
    energy_results_drag = []

    print("\nStarte Parameterstudie 2: Einfluss des Luftwiderstandes:")

    for drag_area in test_drag_areas:
        config = SimulationConfig(
            smoothing_enabled=True,
            drag_area_m2=float(drag_area)
        )

        route = RouteAnalyzer(config).analyze(gps_data)
        physics = BikePhysicsModel(config)

        motor = Motor(
            torque_constant_nm_per_a=config.motor_torque_constant_nm_per_a,
            efficiency=config.motor_efficiency,
            max_mechanical_power_w=config.motor_max_mechanical_power_w,
        )

        lipo = LiPoBattery(
            series_cells=10,
            parallel_cells=20,
            cell_capacity_ah=3.0,
            initial_soc=1.0
        )

        nmc = NMCBattery(
            series_cells=10,
            parallel_cells=4,
            cell_capacity_ah=3.0,
            initial_soc=1.0
        )

        simulation = EBikeSimulation(config, physics, motor)
        results, summary = simulation.run(route, [lipo, nmc])

        lipo_end_soc = results["lipo_soc"].iloc[-1]
        consumed_wh = 2220.0 - (lipo_end_soc * 2220.0)

        energy_results_drag.append(consumed_wh)

        print(
            f"- c_w · A: {drag_area:.2f} m² "
            f"-> Verbrauch: {consumed_wh:.2f} Wh"
        )

    plt.figure(figsize=(8, 5))
    plt.plot(
        test_drag_areas,
        energy_results_drag,
        marker="o",
        color="green",
        linewidth=2
    )

    plt.title(
        "Parameterstudie: Einfluss des Luftwiderstandes "
        "auf den Energieverbrauch"
    )
    plt.xlabel("Luftwiderstandsfläche c_w · A / m²")
    plt.ylabel("Verbrauchte Energie (LiPo) / Wh")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(
        output_dir / "study_02_air_resistance.png",
        dpi=160
    )
    plt.close()


if __name__ == "__main__":

    logging.getLogger("ebike_sim").setLevel(logging.WARNING)

    gps_path = Path("data/final_project_input_data.csv")

    run_studies(gps_path)