class EBikeSimulationError(Exception):
    """Basisklasse für fachliche Fehler der Anwendung."""


class GPSDataError(EBikeSimulationError):
    """Ungültige oder unvollständige GPS-Daten."""


class BatteryDepletedError(EBikeSimulationError):
    """Akku ist vollständig entladen."""


class BatteryPowerError(EBikeSimulationError):
    """Angeforderte elektrische Leistung ist mit dem Akku nicht lieferbar."""
