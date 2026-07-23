from pathlib import Path

import pandas as pd

from .simulation import SimulationSummary


def create_latex_report(
    results: pd.DataFrame,
    summary: SimulationSummary,
    output_dir: Path,
) -> Path:
    """Erstellt einen einfachen Fahrtbericht als LaTeX-Datei."""

    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "fahrtbericht.tex"

    max_speed_km_h = 0.0

    if "speed_m_s" in results.columns:
        max_speed_km_h = results["speed_m_s"].max() * 3.6

    average_air_density = 0.0
    minimum_air_density = 0.0
    maximum_air_density = 0.0

    if "air_density_kg_m3" in results.columns:
        average_air_density = results["air_density_kg_m3"].mean()
        minimum_air_density = results["air_density_kg_m3"].min()
        maximum_air_density = results["air_density_kg_m3"].max()

    battery_text = ""

    for battery_name in summary.final_soc_percent:
        final_soc = summary.final_soc_percent[battery_name]
        consumed_energy = summary.consumed_energy_wh[battery_name]

        battery_text += (
            f"{battery_name} & "
            f"{final_soc:.2f} \\% & "
            f"{consumed_energy:.2f} Wh \\\\\n"
        )

    latex_text = rf"""
\documentclass[a4paper,12pt]{{article}}

\usepackage[utf8]{{inputenc}}
\usepackage[ngerman]{{babel}}
\usepackage{{graphicx}}
\usepackage{{float}}
\usepackage{{booktabs}}
\usepackage{{geometry}}

\geometry{{
    left=2.5cm,
    right=2.5cm,
    top=2.5cm,
    bottom=2.5cm
}}

\title{{Fahrtbericht der E-Bike-Simulation}}
\author{{E-Bike-Abschlussprojekt}}
\date{{\today}}

\begin{{document}}

\maketitle

\section{{Zusammenfassung}}

In diesem Bericht werden die wichtigsten Ergebnisse der
E-Bike-Simulation dargestellt.

Die Strecke wurde aus GPS-Daten ausgewertet. Anschließend wurden
Geschwindigkeit, Beschleunigung, Steigung, Fahrwiderstände,
Motorleistung und Akkuverbrauch berechnet.

\section{{Kenngrößen der Fahrt}}

\begin{{table}}[H]
\centering
\begin{{tabular}}{{lr}}
\toprule
Kenngröße & Wert \\
\midrule
Strecke & {summary.total_distance_km:.2f} km \\
Fahrtdauer & {summary.duration_min:.2f} min \\
Durchschnittsgeschwindigkeit &
{summary.average_speed_km_h:.2f} km/h \\
Maximalgeschwindigkeit & {max_speed_km_h:.2f} km/h \\
Höhenmeter Anstieg & {summary.ascent_m:.1f} m \\
Höhenmeter Abstieg & {summary.descent_m:.1f} m \\
Maximal benötigte Leistung &
{summary.max_required_power_w:.1f} W \\
Maximale Motorleistung &
{summary.max_motor_power_w:.1f} W \\
Motorbegrenzungen &
{summary.motor_power_limit_count} \\
\bottomrule
\end{{tabular}}
\caption{{Wichtigste Ergebnisse der Fahrt}}
\end{{table}}

\section{{Luftdichte}}

Die Luftdichte wird während der Simulation aus der Höhe und der
eingestellten Umgebungstemperatur berechnet.

\begin{{table}}[H]
\centering
\begin{{tabular}}{{lr}}
\toprule
Kenngröße & Wert \\
\midrule
Mittlere Luftdichte &
{average_air_density:.4f} kg/m³ \\
Minimale Luftdichte &
{minimum_air_density:.4f} kg/m³ \\
Maximale Luftdichte &
{maximum_air_density:.4f} kg/m³ \\
\bottomrule
\end{{tabular}}
\caption{{Luftdichte während der Fahrt}}
\end{{table}}

\section{{Akkuvergleich}}

\begin{{table}}[H]
\centering
\begin{{tabular}}{{lrr}}
\toprule
Akkutyp & End-SOC & Energieverbrauch \\
\midrule
{battery_text}
\bottomrule
\end{{tabular}}
\caption{{Vergleich der verwendeten Akkumodelle}}
\end{{table}}

\section{{Diagramme}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.9\textwidth]{{01_geschwindigkeit.png}}
\caption{{Geschwindigkeit während der Fahrt}}
\end{{figure}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.9\textwidth]{{03_hoehenprofil.png}}
\caption{{Höhenprofil der Strecke}}
\end{{figure}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.9\textwidth]{{04_leistung.png}}
\caption{{Benötigte Leistung und Motorleistung}}
\end{{figure}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.9\textwidth]{{07_ladezustand.png}}
\caption{{Ladezustand der Akkus}}
\end{{figure}}


\end{{document}}
"""

    report_path.write_text(
        latex_text,
        encoding="utf-8",
    )

    return report_path