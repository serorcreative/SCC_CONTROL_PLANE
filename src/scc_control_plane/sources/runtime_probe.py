"""Source d'observation : sonde déterministe du Runtime SCC.

Supervise le Runtime **via ses points d'extension publics**, sans le modifier :

* injection d'une horloge et d'une fabrique d'identifiants **déterministes**
  (``FixedClock`` + ``SequentialFactory``) → jobs/événements rejouables ;
* abonnement au journal d'événements (``EventLog.subscribe``) → supervision des
  événements en direct ;
* superviseur enregistreur (``RecordingSupervisor``) → preuve du branchement BrainAI.

La sonde exécute un scénario borné (echo T1 + action T3 sous garde-fou) et renvoie
une observation structurée : sessions, jobs, événements, décisions de gouvernance.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any, Dict, List

from scc_control_plane.core.config import ControlPlaneConfig
from scc_control_plane.core.errors import SourceUnavailable


class RuntimeProbe:
    def __init__(self, config: ControlPlaneConfig):
        self._config = config
        self._rt = None

    def _ensure(self):
        if self._rt is not None:
            return self._rt
        src = self._config.runtime_src
        if not src.exists():
            raise SourceUnavailable(f"Runtime SCC introuvable : {src}")
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
        try:
            self._rt = importlib.import_module("scc_runtime")
        except ImportError as exc:  # pragma: no cover
            raise SourceUnavailable(f"Import du Runtime impossible : {exc}") from exc
        return self._rt

    @property
    def available(self) -> bool:
        try:
            self._ensure()
            return True
        except SourceUnavailable:
            return False

    def probe(self) -> Dict[str, Any]:
        """Exécute un scénario déterministe et renvoie l'observation du Runtime."""
        rt = self._ensure()
        from scc_runtime.core.clock import FixedClock, SequentialFactory

        supervisor = rt.RecordingSupervisor()
        engine = rt.RuntimeEngine(
            clock=FixedClock(self._config.as_of),
            id_factory=SequentialFactory(),
            supervisor=supervisor,
        )

        # Supervision des événements : abonnement au journal (point d'extension).
        collected: List[Dict[str, Any]] = []
        engine.events.subscribe(lambda e: collected.append(e.to_dict()))

        engine.boot()
        session = engine.open_session(actor="control-plane",
                                      autonomy=rt.AutonomyLevel.A3,
                                      label="Supervision — sonde déterministe")
        # Job T1 hermétique.
        engine.submit(session.id, rt.JobKind.ECHO, {"message": "probe"})
        # Job T3 : bloqué par la règle dure, validé humainement (garde-fou observé).
        t3 = engine.submit(session.id, rt.JobKind.SENSITIVE_ACTION, {"target": "probe_action"})
        t3_blocked = t3.status.value == "blocked"
        if t3_blocked:
            engine.approve(t3.id, approver="control-plane-human")
        engine.run_all()

        snapshot = engine.state.snapshot()
        check = engine.self_check()

        # Agrégats déterministes.
        def hist(items, key):
            h: Dict[str, int] = {}
            for it in items:
                h[it[key]] = h.get(it[key], 0) + 1
            return dict(sorted(h.items()))

        jobs = snapshot["jobs"]
        gov = {
            "decisions": sum(1 for e in collected if e["type"] == "governance.decision"),
            "blocked": sum(1 for e in collected if e["type"] == "job.blocked"),
            "approvals": sum(1 for e in collected if e["type"] == "governance.approval"),
            "refused": sum(1 for e in collected if e["type"] == "job.refused"),
        }
        result = {
            "runtime_state": snapshot["runtime_state"],
            "sessions": snapshot["sessions"],
            "jobs": jobs,
            "counts": snapshot["counts"],
            "jobs_by_status": hist(jobs, "status"),
            "jobs_by_trust": hist(jobs, "trust"),
            "events": collected,
            "events_by_type": hist(collected, "type"),
            "governance": gov,
            "t3_guardrail_observed": t3_blocked,
            "self_check": check.to_dict(),
            "kinds": engine.registry.kinds(),
            "vetos": engine.policies.veto_names,
            "supervisor": {
                "name": supervisor.name,
                "plans": len(supervisor.plans),
                "reviews": len(supervisor.reviews),
                "decisions": len(supervisor.decisions),
            },
        }
        engine.shutdown()
        return result


__all__ = ["RuntimeProbe"]
