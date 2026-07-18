import pytest

from ebike_sim.battery import LiPoBattery, NMCBattery


def test_lipo_ocv_limits() -> None:
    battery = LiPoBattery()
    assert battery.pack_ocv_v(0.0) == pytest.approx(32.0)
    assert battery.pack_ocv_v(1.0) == pytest.approx(42.0)


def test_nmc_ocv_limits() -> None:
    battery = NMCBattery()
    assert battery.pack_ocv_v(0.0) == pytest.approx(32.0)
    assert battery.pack_ocv_v(1.0) == pytest.approx(42.0)


def test_discharge_reduces_soc() -> None:
    battery = LiPoBattery(initial_soc=1.0)
    battery.step(requested_power_w=200.0, delta_t_s=60.0)
    assert battery.soc < 1.0
    assert battery.soc >= 0.0
