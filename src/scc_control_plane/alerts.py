"""Journal des alertes — moteur de règles déterministe.

À partir des observations, un ensemble de **règles pures** émet des :class:`Alert`
(id dérivé du code + sujet, horodatage figé ``as_of``). Le journal est ordonné et
sérialisable en JSONL. Mêmes observations ⇒ mêmes alertes (déterminisme total).

Les règles ne *jugent* pas l'architecture : elles signalent des écarts observables
(composant absent, arête invalide, job échoué, garde-fou T3, orphelins…).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from scc_control_plane.core.model import Alert, Severity


class AlertJournal:
    """Collection ordonnée et déterministe d'alertes."""

    def __init__(self, as_of: str):
        self._as_of = as_of
        self._alerts: List[Alert] = []
        self._seen = set()

    def raise_alert(self, code: str, severity: Severity, subject: str, message: str,
                    source: str = "control_plane") -> None:
        alert = Alert(code=code, severity=severity, subject=subject, message=message,
                      timestamp=self._as_of, source=source)
        if alert.id in self._seen:
            return
        self._seen.add(alert.id)
        self._alerts.append(alert)

    @property
    def alerts(self) -> List[Alert]:
        # tri déterministe : sévérité décroissante puis id.
        order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
        return sorted(self._alerts, key=lambda a: (order[a.severity.value], a.id))

    def by_severity(self) -> Dict[str, int]:
        h: Dict[str, int] = {}
        for a in self._alerts:
            h[a.severity.value] = h.get(a.severity.value, 0) + 1
        return dict(sorted(h.items()))

    def to_list(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self.alerts]

    def dump(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(json.dumps(a.to_dict(), ensure_ascii=False) for a in self.alerts)
        path.write_text(content + ("\n" if content else ""), encoding="utf-8")
        return path


def evaluate_rules(as_of: str, *, global_state: Dict[str, Any],
                   component_health: List[Dict[str, Any]], graph: Dict[str, Any],
                   runtime: Dict[str, Any], agents: Dict[str, Any]) -> AlertJournal:
    """Applique les règles d'alerte aux observations et renvoie le journal."""
    journal = AlertJournal(as_of)

    # R1 — composant absent.
    for c in component_health:
        if c["state"] == "down":
            journal.raise_alert("component_missing", Severity.ERROR, c["name"],
                                f"Composant absent ou injoignable : {c['name']}.")

    # R2 — arêtes invalides dans le graphe.
    invalid = graph.get("edges_invalid", 0)
    if invalid:
        journal.raise_alert("graph_invalid_edges", Severity.ERROR, "graph",
                            f"{invalid} relation(s) hors grammaire dans le graphe.")

    # R3 — orphelins de graphe (bénins mais signalés).
    orphans = graph.get("orphans", 0)
    if orphans:
        journal.raise_alert("graph_orphans", Severity.WARNING, "graph",
                            f"{orphans} nœud(s) orphelin(s) dans le graphe.")

    # R4 — readiness dégradée.
    verdict = (global_state.get("readiness") or "").upper()
    if verdict and not verdict.startswith("READY"):
        journal.raise_alert("readiness_not_ready", Severity.CRITICAL, "readiness",
                            f"Verdict de préparation : {verdict}.")
    elif "WARNING" in verdict:
        journal.raise_alert("readiness_warnings", Severity.INFO, "readiness",
                            "Préparation READY WITH WARNINGS (avertissements ouverts).")

    # R5 — prérequis non levés.
    if global_state.get("prerequisites_cleared") is False:
        journal.raise_alert("prerequisites_open", Severity.WARNING, "readiness",
                            "Des prérequis de readiness restent ouverts.")

    # R6 — jobs Runtime échoués.
    for status, n in runtime.get("jobs_by_status", {}).items():
        if status == "failed" and n:
            journal.raise_alert("runtime_jobs_failed", Severity.ERROR, "runtime",
                                f"{n} job(s) Runtime en échec.")

    # R7 — garde-fou T3 observé (sain : preuve de gouvernance active).
    if runtime.get("t3_guardrail_observed"):
        journal.raise_alert("t3_guardrail_active", Severity.INFO, "runtime",
                            "Garde-fou T3 actif : action critique bloquée puis validée humainement.")

    # R8 — agents sans relation sortante (informationnel).
    for agent_id in agents.get("out_orphans", []):
        journal.raise_alert("agent_out_orphan", Severity.INFO, agent_id,
                            f"Agent sans relation sortante dans le graphe : {agent_id}.")

    return journal


__all__ = ["AlertJournal", "evaluate_rules"]
