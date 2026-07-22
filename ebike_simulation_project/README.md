# GPS-basierte E-Bike-Simulation

Dieses Projekt liest GPS-Daten ein und berechnet daraus Strecke, Geschwindigkeit,
Beschleunigung, Steigung, Fahrwiderstände, Motorleistung, Drehmoment, Motorstrom
sowie den Ladezustand eines LiPo- und eines NMC-Akkus.

## Modellparameter

Vorgegebene Fahrradwerte:

- Fahrermasse: 70 kg
- Fahrradmasse: 10 kg
- Produkt `c_w * A`: 0,5625 m²
- Raddurchmesser: 27 inch
- Motorkonstante: 1,5 Nm/A

Akkus:

- 10SxP
- Nennspannung: 3,7 V/Zelle
- Spannungsbereich: 3,2 bis 4,2 V/Zelle
- LiPo-Innenwiderstand: 8 mOhm/Zelle
- NMC-Innenwiderstand: 7 mOhm/Zelle
- OCV-SOC-Kennlinien entsprechend der Aufgabenstellung

Da weder `x` noch die Zellkapazität vorgegeben wurden, verwendet `main.py`
standardmäßig **10S4P mit 3,0 Ah pro Zelle**. Das entspricht nominell etwa
444 Wh. Diese beiden Werte können direkt in `main.py` verändert werden.

## Installation

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Pakete installieren:

```bash
pip install -r requirements.txt
pip install -e .
```

## Erwartetes CSV-Format

```csv
timestamp,latitude,longitude,elevation_m
2026-01-01T10:00:00Z,47.0,11.0,500.0
```

Viele deutsche und englische Alternativnamen werden automatisch erkannt,
beispielsweise `Zeitstempel`, `Breitengrad`, `Längengrad` und `Höhe`.

## Start

```bash
python main.py data/example_gps.csv
```

Optional:

```bash
python main.py meine_fahrt.csv --output-dir ergebnisse
python main.py meine_fahrt.csv --delimiter ";"
python main.py meine_fahrt.csv --no-smoothing
```

## Ergebnisse

Im Ausgabeordner entstehen:

- `simulation_results.csv`
- `summary.txt`
- `simulation.log`
- Diagramme zu Geschwindigkeit, Beschleunigung, Höhe, Leistung, Drehmoment,
  Motorstrom, Ladezustand und Akkuspannung

## Physikalisches Modell

Die notwendige Kraft wird berechnet als:

```text
F = m*a + m*g*sin(phi) + c_r*m*g*cos(phi) + 0.5*rho*c_w*A*v²
```

Die mechanische Leistung ist:

```text
P = F*v
```

Das Drehmoment am Rad ist:

```text
T = F_motor*r
```

Der vereinfachte Motorstrom ist:

```text
I_motor = T / K_m
```

Der Batteriestrom wird zusätzlich aus Open-Circuit-Spannung und
Innenwiderstand berechnet:

```text
P = (U_oc - I*R)*I
```

## Wichtige Modellgrenzen

GPS-Höhen- und Positionswerte enthalten Messrauschen. Das Programm glättet
deshalb Höhe und Geschwindigkeit. Für eine wissenschaftlich belastbare
Auslegung sollten die Filterparameter anhand des echten Datensatzes geprüft
werden.

Die Aufgabenstellung nennt keine Fahrerleistung, keine konkrete Zellkapazität,
keine Parallelzahl, keinen Rollwiderstand und keinen Motorwirkungsgrad.
Diese Werte sind deshalb konfigurierbar und in `SimulationConfig` dokumentiert.

## Berechnung der Luftdichte

Die Luftdichte wird aus der Höhe über dem Meeresspiegel und der
Umgebungstemperatur bestimmt. Dazu werden die barometrische
Höhenformel und die ideale Gasgleichung verwendet.

Die berechnete Luftdichte wird anschließend zur Bestimmung der
Luftwiderstandskraft verwendet:

F_Luft = 0.5 · rho · c_w · A · v²

Die Berechnung geht von trockener Luft aus. Der Einfluss der
Luftfeuchtigkeit wird nicht berücksichtigt.

## Tests

```bash
pytest
```
## Unit Tests

Die Unit Tests können mit folgendem Befehl ausgeführt werden:

```bash
python -m pytest

## UML-Klassendiagramm

```mermaid
classDiagram
    class GPSDataReader {
        +read(file_path) DataFrame
    }
    class RouteAnalyzer {
        +analyze(gps) DataFrame
    }
    class BikePhysicsModel {
        +calculate(route) DataFrame
    }
    class Motor {
        +calculate(data, wheel_radius_m) DataFrame
    }
    class Battery {
        <<abstract>>
        +step(power, delta_t) BatteryStep
        +pack_ocv_v(soc) float
    }
    class LiPoBattery
    class NMCBattery
    class EBikeSimulation {
        +run(route, batteries)
    }
    class ResultVisualizer {
        +create_all(data, output_dir)
    }

    Battery <|-- LiPoBattery
    Battery <|-- NMCBattery
    GPSDataReader --> RouteAnalyzer
    RouteAnalyzer --> EBikeSimulation
    BikePhysicsModel --> EBikeSimulation
    Motor --> EBikeSimulation
    Battery --> EBikeSimulation
    EBikeSimulation --> ResultVisualizer
```

## Aktivitätsdiagramm

```mermaid
flowchart TD
    A[Programmstart] --> B[GPS-Datei einlesen]
    B --> C{Daten gültig?}
    C -- Nein --> D[Fehler loggen und Programm beenden]
    C -- Ja --> E[GPS-Daten sortieren und glätten]
    E --> F[Strecke und Zeitdifferenzen berechnen]
    F --> G[Geschwindigkeit, Beschleunigung und Steigung berechnen]
    G --> H[Fahrwiderstände und Leistung berechnen]
    H --> I[Drehmoment und Motorstrom berechnen]
    I --> J[LiPo-Akku simulieren]
    J --> K[NMC-Akku simulieren]
    K --> L[Ergebnisdatei und Kennwerte erzeugen]
    L --> M[Diagramme speichern]
    M --> N[Programmende]
```
