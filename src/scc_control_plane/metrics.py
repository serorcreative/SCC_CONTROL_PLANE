"""Métriques d'activité — agrégats déterministes de l'état de SCC.

Les métriques sont **dérivées** des observations (API + sonde Runtime) : elles ne
mesurent rien de nouveau, elles chiffrent ce que les moniteurs constatent. Groupées
par domaine et sérialisables (prêtes pour un futur tableau de bord).
"""

from __future__ import annotations

from typing import Any, Dict, List

from scc_control_plane.core.model import Metric
from scc_control_plane.monitors import AgentsMonitor, EnginesMonitor, RuntimeMonitor, SystemMonitor
from scc_control_plane.sources.api_source import ApiSource


class MetricsCollector:
    def __init__(self, api: ApiSource, system: SystemMonitor, runtime: RuntimeMonitor,
                 agents: AgentsMonitor, engines: EnginesMonitor):
        self._api = api
        self._system = system
        self._runtime = runtime
        self._agents = agents
        self._engines = engines

    def collect(self) -> Dict[str, Dict[str, Any]]:
        groups: Dict[str, Dict[str, Any]] = {}

        gs = self.global_or_empty()
        graph = (gs.get("graph") or {})
        groups["system"] = {
            "components_present": _num(gs.get("components_present")),
            "readiness": gs.get("readiness"),
            "prerequisites_cleared": gs.get("prerequisites_cleared"),
        }
        groups["graph"] = {
            "nodes": graph.get("nodes", 0),
            "edges": graph.get("edges", 0),
            "edges_valid": graph.get("edges_valid", 0),
            "edges_invalid": graph.get("edges_invalid", 0),
            "orphans": graph.get("orphans", 0),
        }

        inv = self._api.inventory()
        cats = inv.get("catalogs", {})
        groups["catalog"] = {
            "doctrines": cats.get("doctrines", 0),
            "capabilities": cats.get("capabilities", 0),
            "skills": cats.get("skills", 0),
            "workflows": cats.get("workflows", 0),
            "agents": cats.get("agents", 0),
            "total": inv.get("catalog_total", 0),
        }

        rt = self._runtime.observe()
        groups["runtime"] = {
            "sessions": rt["counts"]["sessions"],
            "jobs": rt["counts"]["jobs"],
            "jobs_succeeded": rt["jobs_by_status"].get("succeeded", 0),
            "events": len(rt["events"]),
            "governance_decisions": rt["governance"]["decisions"],
            "governance_approvals": rt["governance"]["approvals"],
            "t3_guardrail_observed": rt["t3_guardrail_observed"],
        }

        ag = self._agents.supervise()
        groups["agents"] = {"total": ag["total"], "out_orphans": len(ag["out_orphans"])}

        en = self._engines.supervise()
        groups["engines"] = {"present": sum(1 for e in en["engines"].values() if e["present"])}

        return groups

    def global_or_empty(self) -> Dict[str, Any]:
        try:
            return self._system.global_state()
        except Exception:  # noqa: BLE001
            return {}

    def flat(self) -> List[Dict[str, Any]]:
        """Liste plate de métriques (name, value, group) — format tableau de bord."""
        out: List[Dict[str, Any]] = []
        for group, kv in self.collect().items():
            for name, value in kv.items():
                out.append(Metric(name=name, value=value, group=group)._asdict())
        return out


def _num(text) -> int:
    """Extrait l'entier de gauche d'une valeur du type '11/11'."""
    if isinstance(text, int):
        return text
    try:
        return int(str(text).split("/")[0])
    except (ValueError, AttributeError):
        return 0


__all__ = ["MetricsCollector"]
