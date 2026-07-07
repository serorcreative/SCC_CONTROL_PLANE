"""ControlPlane — façade officielle de supervision et d'observabilité de SCC.

Point d'entrée unique de la couche. Orchestre les sources (API, sonde Runtime) et
les moniteurs pour produire : état global, santé des composants, supervision
(Runtime, jobs, sessions, agents, moteurs, événements), métriques, alertes,
diagnostics, auto-vérifications et rapports d'état consolidés.

Invariants : lecture/observation seulement ; aucun moteur, Runtime ou API modifié ;
aucun LLM ; aucun réseau ; stdlib pur ; **déterminisme total** (horodatage figé).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from scc_control_plane.alerts import evaluate_rules
from scc_control_plane.core.config import ControlPlaneConfig, load_config
from scc_control_plane.core.model import ComponentHealth, HealthState, Report, worst
from scc_control_plane.diagnostics import run_diagnostics
from scc_control_plane.metrics import MetricsCollector
from scc_control_plane.monitors import AgentsMonitor, EnginesMonitor, RuntimeMonitor, SystemMonitor
from scc_control_plane.sources.api_source import ApiSource
from scc_control_plane.sources.runtime_probe import RuntimeProbe


class ControlPlane:
    def __init__(self, config: Optional[ControlPlaneConfig] = None):
        self.config = config or load_config()
        self.api = ApiSource(self.config)
        self.probe = RuntimeProbe(self.config)
        self.system = SystemMonitor(self.api)
        self.runtime = RuntimeMonitor(self.probe)
        self.agents = AgentsMonitor(self.api)
        self.engines = EnginesMonitor(self.api)
        self.metrics_collector = MetricsCollector(
            self.api, self.system, self.runtime, self.agents, self.engines)

    # ================================================================== #
    # État & santé
    # ================================================================== #
    def global_state(self) -> Dict[str, Any]:
        return self.system.global_state()

    def component_health(self) -> Dict[str, Any]:
        comps = self.system.component_health()
        overall = worst(c.state for c in comps)
        return {"overall": overall.value,
                "components": [c.to_dict() for c in comps]}

    def health(self) -> Dict[str, Any]:
        """Rollup de santé de tous les domaines supervisés."""
        domains: List[ComponentHealth] = []
        domains.extend(self.system.component_health())
        for producer in (self.system.health, self.runtime.health,
                         self.agents.health, self.engines.health):
            try:
                domains.append(producer())
            except Exception as exc:  # noqa: BLE001 - domaine indisponible => DOWN
                domains.append(ComponentHealth(getattr(producer, "__name__", "domaine"),
                                               HealthState.DOWN, str(exc)))
        overall = worst(d.state for d in domains)
        return {
            "overall": overall.value,
            "as_of": self.config.as_of,
            "domains": [d.to_dict() for d in domains],
        }

    # ================================================================== #
    # Supervision par domaine
    # ================================================================== #
    def supervise_runtime(self) -> Dict[str, Any]:
        obs = self.runtime.observe()
        return {
            "runtime_state": obs["runtime_state"],
            "health": self.runtime.health().to_dict(),
            "kinds": obs["kinds"],
            "vetos": obs["vetos"],
            "supervisor": obs["supervisor"],
            "self_check": obs["self_check"],
        }

    def supervise_jobs(self) -> Dict[str, Any]:
        return self.runtime.jobs()

    def supervise_sessions(self) -> Dict[str, Any]:
        return self.runtime.sessions()

    def supervise_events(self) -> Dict[str, Any]:
        return self.runtime.events()

    def supervise_agents(self) -> Dict[str, Any]:
        return self.agents.supervise()

    def supervise_engines(self) -> Dict[str, Any]:
        return self.engines.supervise()

    # ================================================================== #
    # Métriques, alertes, diagnostics
    # ================================================================== #
    def metrics(self) -> Dict[str, Any]:
        return {"as_of": self.config.as_of,
                "groups": self.metrics_collector.collect(),
                "flat": self.metrics_collector.flat()}

    def alerts(self) -> Dict[str, Any]:
        journal = self._journal()
        return {
            "as_of": self.config.as_of,
            "count": len(journal.alerts),
            "by_severity": journal.by_severity(),
            "alerts": journal.to_list(),
        }

    def _journal(self):
        comp = self.system.component_health()
        return evaluate_rules(
            self.config.as_of,
            global_state=self._safe(self.system.global_state),
            component_health=[c.to_dict() for c in comp],
            graph=self._safe(self.api.graph_summary).get("counts", {}),
            runtime=self.runtime.observe(),
            agents=self.agents.supervise(),
        )

    def diagnostics(self) -> Dict[str, Any]:
        return run_diagnostics(self.config, self.api, self.probe).to_dict()

    def self_check(self) -> Dict[str, Any]:
        """Auto-vérification de la couche de supervision elle-même."""
        report = Report("Control Plane — auto-vérification")
        report.add("api_source", self.api.available, "API SCC joignable")
        report.add("runtime_probe", self.probe.available, "sonde Runtime disponible")
        report.add("deterministic_clock", bool(self.config.as_of),
                   f"as_of={self.config.as_of}")
        try:
            self.config.ensure_directories()
            report.add("state_dir_writable", self.config.state_dir.exists(),
                       str(self.config.state_dir))
        except Exception as exc:  # noqa: BLE001
            report.add("state_dir_writable", False, str(exc))
        report.add("no_llm_no_network", True,
                   "couche d'observation stdlib ; aucun client LLM/réseau")
        return report.to_dict()

    # ================================================================== #
    # Rapports d'état & snapshot
    # ================================================================== #
    def state_report(self) -> Dict[str, Any]:
        """Rapport d'état consolidé (document unique d'observabilité)."""
        return {
            "as_of": self.config.as_of,
            "global_state": self._safe(self.system.global_state),
            "health": self.health(),
            "metrics": self.metrics()["groups"],
            "runtime": self.supervise_runtime(),
            "jobs": self.supervise_jobs(),
            "sessions": self.supervise_sessions(),
            "events": self.supervise_events(),
            "agents": self.supervise_agents(),
            "engines": self.supervise_engines(),
            "alerts": self.alerts(),
            "diagnostics": self.diagnostics(),
            "self_check": self.self_check(),
        }

    def snapshot(self) -> Dict[str, Any]:
        """Alias explicite : instantané complet (base d'un tableau de bord BrainAI)."""
        return self.state_report()

    def write_state_report(self, tag: str = "state") -> Dict[str, str]:
        """Persiste le rapport (JSON + Markdown) et le journal d'alertes (JSONL)."""
        self.config.ensure_directories()
        report = self.state_report()
        json_path = self.config.state_dir / f"{tag}_report.json"
        md_path = self.config.state_dir / f"{tag}_report.md"
        alerts_path = self.config.state_dir / f"{tag}_alerts.jsonl"

        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        md_path.write_text(_render_markdown(report), encoding="utf-8")
        self._journal().dump(alerts_path)
        return {"json": str(json_path), "markdown": str(md_path), "alerts": str(alerts_path)}

    # -- helpers -------------------------------------------------------- #
    @staticmethod
    def _safe(fn) -> Dict[str, Any]:
        try:
            return fn()
        except Exception:  # noqa: BLE001
            return {}


def _render_markdown(report: Dict[str, Any]) -> str:
    g = report.get("global_state", {})
    h = report.get("health", {})
    a = report.get("alerts", {})
    lines = [
        "# SCC — Rapport d'état (Control Plane)",
        "",
        f"> Instantané déterministe — `as_of` : {report.get('as_of')}",
        "",
        "## Santé globale",
        "",
        f"- **État global** : `{h.get('overall')}`",
        f"- **Composants présents** : {g.get('components_present')}",
        f"- **Readiness** : {g.get('readiness')}",
        f"- **Prérequis levés** : {g.get('prerequisites_cleared')}",
        "",
        "## Santé par domaine",
        "",
        "| Domaine | État | Détail |",
        "|---------|------|--------|",
    ]
    for d in h.get("domains", []):
        lines.append(f"| {d['name']} | `{d['state']}` | {d.get('detail','')} |")
    lines += ["", "## Alertes", "",
              f"- **Total** : {a.get('count')} — répartition : {a.get('by_severity')}", ""]
    for al in a.get("alerts", []):
        lines.append(f"- `{al['severity']}` **{al['code']}** ({al['subject']}) — {al['message']}")
    diag = report.get("diagnostics", {})
    lines += ["", "## Diagnostics", "",
              f"- **OK** : {diag.get('ok')} — {diag.get('passed')}/{diag.get('passed',0)+diag.get('failed',0)} vérifications", ""]
    lines.append("*Rapport généré par le Control Plane SCC — déterministe, sans réseau ni LLM.*")
    return "\n".join(lines) + "\n"


__all__ = ["ControlPlane"]
