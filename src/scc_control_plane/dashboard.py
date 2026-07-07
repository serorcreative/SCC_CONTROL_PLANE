"""Modèle de tableau de bord — structure de données, **sans interface graphique**.

Le Control Plane ne dessine rien. Il produit un **modèle de panneaux** (données
pures) qu'un futur tableau de bord BrainAI mappera sur des widgets. Chaque panneau
déclare un ``kind`` d'affichage abstrait (``status``, ``metric_grid``, ``table``,
``alert_list``) et ses données ; le rendu est laissé au consommateur.

C'est la préparation explicite au tableau de bord BrainAI exigée par le chantier :
une frontière nette entre **observabilité** (ici) et **présentation** (plus tard).
"""

from __future__ import annotations

from typing import Any, Dict, List

from scc_control_plane.control_plane import ControlPlane


def _panel(pid: str, title: str, kind: str, data: Any) -> Dict[str, Any]:
    return {"id": pid, "title": title, "kind": kind, "data": data}


def dashboard_model(cp: ControlPlane) -> Dict[str, Any]:
    """Construit le modèle de tableau de bord (panneaux) à partir d'un instantané."""
    snap = cp.snapshot()
    g = snap["global_state"]
    h = snap["health"]
    metrics = snap["metrics"]
    alerts = snap["alerts"]

    panels: List[Dict[str, Any]] = []

    panels.append(_panel("overview", "État global", "status", {
        "overall": h.get("overall"),
        "readiness": g.get("readiness"),
        "components_present": g.get("components_present"),
        "prerequisites_cleared": g.get("prerequisites_cleared"),
        "as_of": snap["as_of"],
    }))

    panels.append(_panel("health_domains", "Santé par domaine", "table", {
        "columns": ["domaine", "état", "détail"],
        "rows": [[d["name"], d["state"], d["detail"]] for d in h.get("domains", [])],
    }))

    panels.append(_panel("metrics", "Métriques d'activité", "metric_grid", metrics))

    panels.append(_panel("runtime", "Supervision Runtime", "table", {
        "columns": ["clé", "valeur"],
        "rows": [
            ["état", snap["runtime"]["runtime_state"]],
            ["jobs", snap["jobs"]["count"]],
            ["jobs par statut", snap["jobs"]["by_status"]],
            ["sessions", snap["sessions"]["count"]],
            ["événements", snap["events"]["count"]],
            ["garde-fou T3", snap["jobs"]["t3_guardrail_observed"]],
        ],
    }))

    panels.append(_panel("engines", "Moteurs", "table", {
        "columns": ["moteur", "présent", "produit", "consomme", "implements"],
        "rows": [[name, e["present"], e["produces"], e["consumes"], e["implements"]]
                 for name, e in snap["engines"]["engines"].items()],
    }))

    panels.append(_panel("agents", "Agents", "metric_grid", {
        "agents": snap["agents"],
    }))

    panels.append(_panel("alerts", "Journal des alertes", "alert_list", {
        "count": alerts["count"],
        "by_severity": alerts["by_severity"],
        "items": alerts["alerts"],
    }))

    panels.append(_panel("diagnostics", "Diagnostics", "status", {
        "ok": snap["diagnostics"]["ok"],
        "passed": snap["diagnostics"]["passed"],
        "failed": snap["diagnostics"]["failed"],
    }))

    return {
        "dashboard": "SCC Control Plane",
        "as_of": snap["as_of"],
        "renderer": "abstrait (aucune interface graphique ; à mapper par le consommateur)",
        "panel_kinds": ["status", "metric_grid", "table", "alert_list"],
        "panels": panels,
    }


def brainai_context(cp: ControlPlane) -> Dict[str, Any]:
    """Contexte d'observabilité read-only destiné à un futur superviseur BrainAI."""
    snap = cp.snapshot()
    return {
        "note": "Observabilité read-only pour BrainAI (aucun LLM ; aucune action ici).",
        "overall_health": snap["health"]["overall"],
        "readiness": snap["global_state"].get("readiness"),
        "alerts_by_severity": snap["alerts"]["by_severity"],
        "diagnostics_ok": snap["diagnostics"]["ok"],
        "metrics": snap["metrics"],
    }


__all__ = ["dashboard_model", "brainai_context"]
