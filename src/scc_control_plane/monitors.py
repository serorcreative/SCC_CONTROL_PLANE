"""Moniteurs du Control Plane — une responsabilité de supervision par domaine.

Chaque moniteur **observe** une facette de SCC en réutilisant les sources (API,
sonde Runtime) et produit une :class:`ComponentHealth` + des vues détaillées. Aucun
moniteur ne réimplémente la logique observée : il l'agrège et la qualifie.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from scc_control_plane.core.model import ComponentHealth, HealthState, worst
from scc_control_plane.sources.api_source import ApiSource
from scc_control_plane.sources.runtime_probe import RuntimeProbe

ENGINE_NODES = {
    "engine_ingestion": "ENG:INGESTION",
    "engine_extraction": "ENG:EXTRACTION",
    "engine_memory": "ENG:MEMORY",
    "engine_knowledge": "ENG:KNOWLEDGE",
    "engine_reasoning": "ENG:REASONING",
}


# --------------------------------------------------------------------------- #
# Système & santé des composants
# --------------------------------------------------------------------------- #
class SystemMonitor:
    def __init__(self, api: ApiSource):
        self._api = api

    def component_health(self) -> List[ComponentHealth]:
        status = self._api.status()
        components = status.get("components", {})
        out: List[ComponentHealth] = []
        for name, info in sorted(components.items()):
            present = info.get("present", False)
            out.append(ComponentHealth(
                name=name,
                state=HealthState.OK if present else HealthState.DOWN,
                detail=info.get("path", ""),
            ))
        return out

    def health(self) -> ComponentHealth:
        api_health = self._api.health()
        state = HealthState.OK if api_health.get("ok") else HealthState.DEGRADED
        return ComponentHealth("api", state,
                               f"{api_health.get('passed')}/{api_health.get('passed', 0) + api_health.get('failed', 0)} checks",
                               metrics={"checks": api_health.get("checks", [])})

    def global_state(self) -> Dict[str, Any]:
        status = self._api.status()
        readiness = self._api.readiness()
        return {
            "components_present": status.get("components_present"),
            "graph": status.get("graph"),
            "runtime_available": status.get("runtime_available"),
            "readiness": readiness.get("verdict"),
            "prerequisites_cleared": readiness.get("prerequisites_cleared"),
        }


# --------------------------------------------------------------------------- #
# Runtime, Jobs, Sessions, Événements (via la sonde déterministe)
# --------------------------------------------------------------------------- #
class RuntimeMonitor:
    def __init__(self, probe: RuntimeProbe):
        self._probe = probe
        self._obs: Optional[Dict[str, Any]] = None

    def observe(self) -> Dict[str, Any]:
        if self._obs is None:
            self._obs = self._probe.probe()
        return self._obs

    def health(self) -> ComponentHealth:
        obs = self.observe()
        failed = obs["jobs_by_status"].get("failed", 0)
        self_ok = obs["self_check"]["ok"]
        if not self_ok:
            state = HealthState.DOWN
        elif failed:
            state = HealthState.DEGRADED
        else:
            state = HealthState.OK
        return ComponentHealth("runtime_exec", state,
                               f"jobs={obs['counts']['jobs']} failed={failed} self_check={self_ok}",
                               metrics={"jobs_by_status": obs["jobs_by_status"]})

    def jobs(self) -> Dict[str, Any]:
        obs = self.observe()
        return {
            "count": obs["counts"]["jobs"],
            "by_status": obs["jobs_by_status"],
            "by_trust": obs["jobs_by_trust"],
            "t3_guardrail_observed": obs["t3_guardrail_observed"],
            "jobs": [{"id": j["id"], "kind": j["kind"], "status": j["status"],
                      "trust": j["trust"], "attempts": j["attempts"]} for j in obs["jobs"]],
        }

    def sessions(self) -> Dict[str, Any]:
        obs = self.observe()
        return {
            "count": obs["counts"]["sessions"],
            "sessions": [{"id": s["id"], "actor": s["actor"], "autonomy": s["autonomy"],
                          "status": s["status"], "jobs": len(s["job_ids"])} for s in obs["sessions"]],
        }

    def events(self) -> Dict[str, Any]:
        obs = self.observe()
        return {
            "count": len(obs["events"]),
            "by_type": obs["events_by_type"],
            "governance": obs["governance"],
        }


# --------------------------------------------------------------------------- #
# Agents
# --------------------------------------------------------------------------- #
class AgentsMonitor:
    def __init__(self, api: ApiSource):
        self._api = api

    def supervise(self) -> Dict[str, Any]:
        agents = self._api.agents()
        by_autonomy: Dict[str, int] = {}
        by_trust: Dict[str, int] = {}
        out_orphans: List[str] = []
        for a in agents:
            meta = a.get("meta", {})
            auto = _first_token(meta.get("Niveau d'autonomie", ""))
            trust = _first_token(meta.get("Niveau de confiance requis", ""))
            if auto:
                by_autonomy[auto] = by_autonomy.get(auto, 0) + 1
            if trust:
                by_trust[trust] = by_trust.get(trust, 0) + 1
            # Connectivité : un agent sans relation sortante dans le graphe.
            try:
                nb = self._api.data("graph.neighbors", {"id": a["id"], "direction": "out"})
                if nb.get("count", 0) == 0:
                    out_orphans.append(a["id"])
            except Exception:  # noqa: BLE001 - agent absent du graphe -> ignoré
                pass
        return {
            "total": len(agents),
            "by_autonomy": dict(sorted(by_autonomy.items())),
            "by_trust": dict(sorted(by_trust.items())),
            "out_orphans": sorted(out_orphans),
        }

    def health(self) -> ComponentHealth:
        data = self.supervise()
        state = HealthState.OK if data["total"] > 0 else HealthState.UNKNOWN
        return ComponentHealth("agents", state,
                               f"{data['total']} agents ; out_orphans={len(data['out_orphans'])}",
                               metrics={"by_autonomy": data["by_autonomy"]})


# --------------------------------------------------------------------------- #
# Moteurs
# --------------------------------------------------------------------------- #
class EnginesMonitor:
    def __init__(self, api: ApiSource):
        self._api = api

    def supervise(self) -> Dict[str, Any]:
        status = self._api.status()
        components = status.get("components", {})
        engines: Dict[str, Any] = {}
        healths: List[HealthState] = []
        for comp, node in ENGINE_NODES.items():
            present = components.get(comp, {}).get("present", False)
            state = HealthState.OK if present else HealthState.DOWN
            healths.append(state)
            entry = {"present": present, "node": node, "produces": [], "consumes": [], "implements": 0}
            try:
                nb = self._api.data("graph.neighbors", {"id": node, "direction": "out"})
                for n in nb.get("neighbors", []):
                    if n["relation"] == "produces":
                        entry["produces"].append(n["node"])
                    elif n["relation"] == "consumes":
                        entry["consumes"].append(n["node"])
                    elif n["relation"] == "implements":
                        entry["implements"] += 1
            except Exception:  # noqa: BLE001
                pass
            engines[comp] = entry
        return {"engines": engines, "state": worst(healths).value}

    def health(self) -> ComponentHealth:
        data = self.supervise()
        return ComponentHealth("engines", HealthState(data["state"]),
                               f"{sum(1 for e in data['engines'].values() if e['present'])}/5 présents",
                               metrics={"count": len(data["engines"])})


def _first_token(value: str) -> str:
    value = (value or "").strip()
    return value.split()[0].split("—")[0].strip() if value else ""


__all__ = ["SystemMonitor", "RuntimeMonitor", "AgentsMonitor", "EnginesMonitor", "ENGINE_NODES"]
