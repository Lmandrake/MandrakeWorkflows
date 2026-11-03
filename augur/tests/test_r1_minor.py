"""Review R1 findings 15, 16, 21, 23: gaps that became measured values, pid reuse, install guard.
Each fixture states its truth directly (a row the test made unparsable, a state the test withheld)."""
import os
import subprocess

import pytest

from augur.collectors import machine as M
from augur.collectors import sessions as S
from augur.darwin import native

import importlib.util as _ilu

_spec = _ilu.spec_from_file_location(
    "_r1_sess_fx", os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_session_collectors.py"))
_sx = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_sx)
FakeReaders, standard, T0 = _sx.FakeReaders, _sx.standard, _sx.T0

AUG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HDR = ",bytes_in,bytes_out,re-tx,\n2.1.292.101,0,0,0,\n"


def flows(*rows):
    return HDR + "".join("tcp4 192.0.2.10:%d<->198.51.100.7:443,%s,\n" % (5000 + i, r)
                         for i, r in enumerate(rows))


def net_ticks(tmp_path, texts):
    w = standard(tmp_path)
    w.shared["session_trees"] = {"101@1793500000": [101]}
    r = FakeReaders({}, {}, [(0, t) for t in texts])
    c = S.SessionNetCollector(r)
    st, out = {}, []
    for i in range(len(texts)):
        out.append(c.collect(w.ctx(T0 + 15 * i, 15.0 * i, st))["sessions.net"])
    return out


# --------------------------------------------------------------------------- finding 15

def test_unparsable_flow_row_makes_the_session_unknown_not_zero(tmp_path):
    out = net_ticks(tmp_path, [flows("1000,2000,0"), flows("??,2000,0")])
    assert out[1]["101@1793500000"] == {"unknown": "read_failed"}


def test_unparsable_row_does_not_corrupt_the_next_delta(tmp_path):
    # truth: the flow moved 1875000 bytes in over the 30 s between the two good readings
    out = net_ticks(tmp_path, [flows("1000,2000,0"), flows("??,2000,0"), flows("1876000,2000,0")])
    v = out[2]["101@1793500000"]
    assert v["rx_mbps"] == pytest.approx(1875000 * 8 / 30 / 1e6, rel=1e-3)   # over its own 30 s


def test_blank_retx_is_no_retx_figure_not_zero(tmp_path):
    out = net_ticks(tmp_path, [flows("1000,2000,5"), flows("1000,902000,")])
    v = out[1]["101@1793500000"]
    assert v["tx_mbps"] == pytest.approx(900000 * 8 / 15 / 1e6, rel=1e-3)
    assert "retx_pct" not in v


# --------------------------------------------------------------------------- finding 16

def test_unreadable_power_state_is_not_on_ac():
    e = native.battery_entry("InternalBattery", None, 50, 100)
    assert e["on_battery"] is None
    assert native.battery_entry("InternalBattery", "AC Power", 50, 100)["on_battery"] is False
    assert native.battery_entry("InternalBattery", "Battery Power", 50, 100)["on_battery"] is True
    class X(object):
        shared = {}
    out = M.PowerCollector({"power": lambda: e}).collect(X())
    assert out["machine.power"] == {"unknown": "read_failed"}
    assert X.shared["on_battery"] is None


# --------------------------------------------------------------------------- finding 23

def test_install_refuses_a_different_home(tmp_path):
    env = dict(os.environ, HOME=str(tmp_path), AUGUR_HOME=str(tmp_path / "ah"))
    r = subprocess.run([os.path.join(AUG, "bin", "install.sh"), "--render-only", str(tmp_path / "x.plist")],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 2 and "HOME" in r.stderr
