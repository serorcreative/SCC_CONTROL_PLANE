"""Tests d'état global et de santé."""

from __future__ import annotations


def test_global_state(cp):
    g = cp.global_state()
    assert g["readiness"].startswith("READY")
    assert g["prerequisites_cleared"] is True


def test_component_health_all_present(cp):
    data = cp.component_health()
    assert data["overall"] == "ok"
    assert all(c["state"] == "ok" for c in data["components"])
    assert len(data["components"]) >= 11


def test_health_rollup(cp):
    h = cp.health()
    assert h["overall"] == "ok"
    assert h["as_of"]
    names = {d["name"] for d in h["domains"]}
    # domaines transverses présents
    assert {"api", "runtime_exec", "agents", "engines"} <= names
