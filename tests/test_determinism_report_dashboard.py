"""Tests de déterminisme, rapport d'état, tableau de bord et contexte BrainAI."""

from __future__ import annotations

import json
from pathlib import Path

from scc_control_plane.control_plane import ControlPlane
from scc_control_plane.dashboard import brainai_context, dashboard_model


def test_snapshot_is_deterministic(config):
    a = ControlPlane(config=config).snapshot()
    b = ControlPlane(config=config).snapshot()
    # Les parties observationnelles doivent être strictement identiques.
    for key in ("metrics", "alerts", "jobs", "sessions", "events", "engines", "agents"):
        assert json.dumps(a[key], sort_keys=True, ensure_ascii=False) == \
               json.dumps(b[key], sort_keys=True, ensure_ascii=False), f"non déterministe : {key}"


def test_write_state_report(cp):
    paths = cp.write_state_report(tag="test")
    for key in ("json", "markdown", "alerts"):
        assert Path(paths[key]).exists()
    # le JSON est relisible et cohérent
    report = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    assert report["health"]["overall"] == "ok"
    # le markdown contient les sections attendues
    md = Path(paths["markdown"]).read_text(encoding="utf-8")
    assert "# SCC — Rapport d'état" in md
    assert "Santé par domaine" in md


def test_dashboard_model(cp):
    dm = dashboard_model(cp)
    ids = {p["id"] for p in dm["panels"]}
    assert {"overview", "health_domains", "metrics", "runtime", "engines", "agents",
            "alerts", "diagnostics"} <= ids
    assert all(p["kind"] in dm["panel_kinds"] for p in dm["panels"])
    # aucune interface graphique : rendu abstrait
    assert "aucune interface graphique" in dm["renderer"]


def test_brainai_context_read_only(cp):
    ctx = brainai_context(cp)
    assert ctx["overall_health"] == "ok"
    assert ctx["diagnostics_ok"] is True
    assert "aucune action" in ctx["note"]
