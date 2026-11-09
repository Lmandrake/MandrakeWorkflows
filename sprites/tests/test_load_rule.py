"""The load-testing refusal: a VPN-up, off-site, stale or missing snapshot must be rejected; only on-site + VPN-not-up passes.
Uses fixture snapshots via SPRITES_AUGUR_SNAPSHOT / a parameter, never the real file, and does no load.
Run: python3 -m pytest sprites/tests/test_load_rule.py"""
import json, os, subprocess, sys
from pathlib import Path
SPR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPR / "tests/tools"))
import load_rule

NOW = 1_000_000.0

def snap(tmp_path, on_site, state, valid_until=NOW + 60):
    p = tmp_path / "snapshot.json"
    p.write_text(json.dumps({"valid_until": valid_until, "machine": {"vpn": {"on_site": on_site, "state": state}}}))
    return p

def test_vpn_up_rejected(tmp_path):
    assert load_rule.refusal(snap(tmp_path, True, "up"), now=NOW) == "VPN is up"

def test_off_site_rejected(tmp_path):
    assert "not on site" in load_rule.refusal(snap(tmp_path, False, "down"), now=NOW)

def test_missing_file_rejected(tmp_path):
    assert "unknown = don't run" in load_rule.refusal(tmp_path / "nope.json", now=NOW)

def test_garbage_and_stale_rejected(tmp_path):
    bad = tmp_path / "bad.json"; bad.write_text("{not json")
    assert load_rule.refusal(bad, now=NOW)
    assert "stale" in load_rule.refusal(snap(tmp_path, True, "down", valid_until=NOW - 1), now=NOW)

def test_on_site_vpn_off_allowed(tmp_path):
    assert load_rule.refusal(snap(tmp_path, True, "down"), now=NOW) is None

def test_gate_refuses_before_running_command(tmp_path):
    """gate.py exits 3 and never runs CMD when the fixture says VPN up (the marker file must not appear)."""
    marker = tmp_path / "ran"
    env = dict(os.environ, SPRITES_AUGUR_SNAPSHOT=str(snap(tmp_path, True, "up", valid_until=9e12)),
               SPRITES_GATE_LOCK=str(tmp_path / ".lock"))
    r = subprocess.run([sys.executable, str(SPR / "tests/tools/gate.py"), "touch", str(marker)], env=env, capture_output=True, text=True)
    assert r.returncode == 3 and "REFUSED" in r.stderr and "on-site network" in r.stderr and not marker.exists()

def test_size_calibrate_refuses_when_snapshot_missing(tmp_path):
    env = dict(os.environ, SPRITES_AUGUR_SNAPSHOT=str(tmp_path / "nope.json"))
    r = subprocess.run([sys.executable, str(SPR / "tools/size_calibrate.py"), "--measure-only"], env=env, capture_output=True, text=True)
    assert r.returncode == 3 and "REFUSED" in r.stderr

GUARDED = ["backdrop_qa", "build_art_review_sheets", "build_gallery", "build_night_vector_sheet", "build_siphon_glow",
           "build_species_style_samples", "build_symbol_comparison", "render_gallery", "species_stills"]

def test_every_browser_render_tool_refuses_when_vpn_up(tmp_path):
    """Each playwright/render tool exits 3 with REFUSED on a VPN-up fixture, before launching anything."""
    env = dict(os.environ, SPRITES_AUGUR_SNAPSHOT=str(snap(tmp_path, True, "up", valid_until=9e12)))
    for t in GUARDED:
        r = subprocess.run([sys.executable, str(SPR / f"tools/{t}.py")], env=env, capture_output=True, text=True, timeout=60)
        assert r.returncode == 3 and "REFUSED" in r.stderr, (t, r.returncode, r.stderr[-300:])
