"""Diagnostics — batterie de vérifications transverses de SCC.

Combine les constats des moniteurs en une série de :class:`Check`. Inclut une
**preuve de déterminisme** : deux sondes indépendantes du Runtime doivent produire
une observation identique (mêmes horloge et fabrique d'identifiants injectées).
"""

from __future__ import annotations

from typing import Any, Dict

from scc_control_plane.core.config import ControlPlaneConfig
from scc_control_plane.core.model import Report
from scc_control_plane.sources.api_source import ApiSource
from scc_control_plane.sources.runtime_probe import RuntimeProbe


def run_diagnostics(config: ControlPlaneConfig, api: ApiSource, probe: RuntimeProbe) -> Report:
    report = Report("SCC — diagnostics transverses")

    # API joignable.
    report.add("api_reachable", api.available, "scc_api localisée et importable")

    # Graphe intègre.
    try:
        g = api.graph_summary()
        counts = g.get("counts", {})
        report.add("graph_loaded", counts.get("nodes", 0) > 0,
                   f"nodes={counts.get('nodes')} edges={counts.get('edges')}")
        report.add("graph_no_invalid_edges", counts.get("edges_invalid", 1) == 0,
                   f"edges_invalid={counts.get('edges_invalid')}")
        report.add("graph_no_dangling", counts.get("dangling_targets", 1) == 0,
                   f"dangling_targets={counts.get('dangling_targets')}")
    except Exception as exc:  # noqa: BLE001
        report.add("graph_loaded", False, str(exc))

    # Composants présents.
    try:
        status = api.status()
        present, total = _ratio(status.get("components_present", "0/0"))
        report.add("components_present", present == total, status.get("components_present"))
    except Exception as exc:  # noqa: BLE001
        report.add("components_present", False, str(exc))

    # Readiness.
    try:
        readiness = api.readiness()
        report.add("readiness_ready", (readiness.get("verdict") or "").upper().startswith("READY"),
                   readiness.get("verdict"))
        report.add("prerequisites_cleared", bool(readiness.get("prerequisites_cleared")),
                   "R-01 & R-02")
    except Exception as exc:  # noqa: BLE001
        report.add("readiness_ready", False, str(exc))

    # Runtime : sonde + self_check + aucun job échoué.
    report.add("runtime_reachable", probe.available, "scc_runtime localisé")
    if probe.available:
        obs = probe.probe()
        report.add("runtime_self_check", obs["self_check"]["ok"], "self_check du Runtime")
        report.add("runtime_no_failed_jobs", obs["jobs_by_status"].get("failed", 0) == 0,
                   f"jobs_by_status={obs['jobs_by_status']}")
        report.add("runtime_t3_guardrail", obs["t3_guardrail_observed"],
                   "action T3 bloquée puis validée humainement")

        # Preuve de déterminisme : deux sondes indépendantes → observation identique.
        probe_b = RuntimeProbe(config)
        obs_b = probe_b.probe()
        same = (_fingerprint(obs) == _fingerprint(obs_b))
        report.add("runtime_deterministic", same,
                   "deux sondes indépendantes produisent une observation identique")

    return report


def _fingerprint(obs: Dict[str, Any]) -> Dict[str, Any]:
    """Empreinte stable d'une observation (ignore rien d'aléatoire : tout est figé)."""
    return {
        "runtime_state": obs["runtime_state"],
        "jobs_by_status": obs["jobs_by_status"],
        "jobs_by_trust": obs["jobs_by_trust"],
        "events_by_type": obs["events_by_type"],
        "governance": obs["governance"],
        "job_ids": [j["id"] for j in obs["jobs"]],
        "session_ids": [s["id"] for s in obs["sessions"]],
        "event_ids": [e["id"] for e in obs["events"]],
    }


def _ratio(text: str):
    try:
        a, b = str(text).split("/")
        return int(a), int(b)
    except (ValueError, AttributeError):
        return 0, 1


__all__ = ["run_diagnostics"]
