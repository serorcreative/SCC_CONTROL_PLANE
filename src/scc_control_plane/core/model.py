"""Modèle d'observabilité du Control Plane : santé, alertes, métriques, rapports.

Structures pures, sérialisables, déterministes. Le vocabulaire de santé et de
sévérité est volontairement minimal et stable (mappable sur un futur tableau de
bord BrainAI sans interface graphique).
"""

from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional


class HealthState(str, Enum):
    """État de santé d'un composant ou du système."""

    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


# Ordre de gravité (pour l'agrégation « pire état »).
_HEALTH_RANK = {"ok": 0, "unknown": 1, "degraded": 2, "down": 3}


def worst(states: Iterable[HealthState]) -> HealthState:
    """Retourne l'état le plus grave d'un ensemble (OK si vide)."""
    worst_state = HealthState.OK
    for s in states:
        if _HEALTH_RANK[s.value] > _HEALTH_RANK[worst_state.value]:
            worst_state = s
    return worst_state


class Severity(str, Enum):
    """Sévérité d'une alerte."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ComponentHealth:
    """Santé d'un composant supervisé."""

    name: str
    state: HealthState
    detail: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "state": self.state.value,
                "detail": self.detail, "metrics": dict(self.metrics)}


@dataclass
class Alert:
    """Fait de supervision signalé (déterministe : id dérivé du code + sujet)."""

    code: str
    severity: Severity
    subject: str
    message: str
    timestamp: str
    source: str = "control_plane"

    @property
    def id(self) -> str:
        subj = self.subject.replace(":", "_").replace("/", "_").replace(" ", "_")
        return f"alert:{self.code}:{subj}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "severity": self.severity.value,
            "subject": self.subject,
            "message": self.message,
            "timestamp": self.timestamp,
            "source": self.source,
        }


# Un point de métrique = un nom, une valeur, un groupe (namespace).
Metric = namedtuple("Metric", ["name", "value", "group"])

Check = namedtuple("Check", ["label", "passed", "detail"])


class Report:
    """Agrège des :class:`Check` et expose ``ok`` (contrat commun SCC)."""

    def __init__(self, title: str, checks: Optional[Iterable[Check]] = None):
        self.title = title
        self.checks: List[Check] = list(checks) if checks else []

    @property
    def ok(self) -> bool:
        return all(c.passed for c in self.checks)

    def add(self, label: str, passed: bool, detail: str = "") -> Check:
        check = Check(label, passed, detail)
        self.checks.append(check)
        return check

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "ok": self.ok,
            "passed": sum(1 for c in self.checks if c.passed),
            "failed": sum(1 for c in self.checks if not c.passed),
            "checks": [{"label": c.label, "passed": c.passed, "detail": c.detail} for c in self.checks],
        }


__all__ = [
    "HealthState", "worst", "Severity", "ComponentHealth",
    "Alert", "Metric", "Check", "Report",
]
