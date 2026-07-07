"""Tests métriques, alertes, diagnostics et auto-vérifications."""

from __future__ import annotations


def test_metrics_groups(cp):
    groups = cp.metrics()["groups"]
    assert groups["graph"]["nodes"] == 197
    assert groups["graph"]["edges_invalid"] == 0
    assert groups["catalog"]["total"] == 173
    assert groups["runtime"]["jobs_succeeded"] == 2
    assert groups["engines"]["present"] == 5


def test_metrics_flat_shape(cp):
    flat = cp.metrics()["flat"]
    assert all({"name", "value", "group"} <= set(m) for m in flat)


def test_alerts_deterministic_content(cp):
    data = cp.alerts()
    codes = {a["code"] for a in data["alerts"]}
    assert "graph_orphans" in codes           # 4 documents orphelins
    assert "t3_guardrail_active" in codes      # garde-fou observé
    assert "readiness_warnings" in codes
    assert data["by_severity"].get("info", 0) >= 1


def test_alerts_have_stable_ids(cp):
    ids = [a["id"] for a in cp.alerts()["alerts"]]
    assert len(ids) == len(set(ids))           # ids uniques
    assert all(i.startswith("alert:") for i in ids)


def test_diagnostics_ok_and_deterministic_check(cp):
    diag = cp.diagnostics()
    assert diag["ok"] is True
    labels = {c["label"] for c in diag["checks"]}
    assert "runtime_deterministic" in labels
    assert next(c for c in diag["checks"] if c["label"] == "runtime_deterministic")["passed"]


def test_self_check(cp):
    sc = cp.self_check()
    assert sc["ok"] is True
    labels = {c["label"] for c in sc["checks"]}
    assert {"api_source", "runtime_probe", "no_llm_no_network"} <= labels
