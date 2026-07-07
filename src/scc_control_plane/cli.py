"""CLI du Control Plane SCC (``scc-control``).

Expose chaque capacité de supervision comme sous-commande, sortie JSON. Miroir de
la façade :class:`~scc_control_plane.control_plane.ControlPlane`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, List, Optional

from scc_control_plane import __version__
from scc_control_plane.control_plane import ControlPlane
from scc_control_plane.core.config import load_config
from scc_control_plane.dashboard import brainai_context, dashboard_model


def _out(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _cp(args) -> ControlPlane:
    return ControlPlane(config=load_config(args.config))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scc-control",
                                     description="Control Plane officiel de Seror Créative Core.")
    parser.add_argument("--version", action="version", version=f"scc-control {__version__}")
    parser.add_argument("--config", type=Path, default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    commands = {
        "state": ("global_state", "État global du système."),
        "health": ("health", "Santé consolidée (rollup)."),
        "components": ("component_health", "Santé des composants."),
        "runtime": ("supervise_runtime", "Supervision Runtime."),
        "jobs": ("supervise_jobs", "Supervision des jobs."),
        "sessions": ("supervise_sessions", "Supervision des sessions."),
        "events": ("supervise_events", "Supervision des événements."),
        "agents": ("supervise_agents", "Supervision des agents."),
        "engines": ("supervise_engines", "Supervision des moteurs."),
        "metrics": ("metrics", "Métriques d'activité."),
        "alerts": ("alerts", "Journal des alertes."),
        "diagnostics": ("diagnostics", "Diagnostics transverses."),
        "self-check": ("self_check", "Auto-vérification du Control Plane."),
        "report": ("state_report", "Rapport d'état consolidé."),
        "snapshot": ("snapshot", "Instantané complet (base tableau de bord)."),
    }
    for name, (method, help_) in commands.items():
        p = sub.add_parser(name, help=help_)
        p.set_defaults(_method=method)

    sub.add_parser("dashboard", help="Modèle de tableau de bord (données, sans GUI).").set_defaults(_method="__dashboard__")
    sub.add_parser("brainai-context", help="Contexte read-only pour BrainAI.").set_defaults(_method="__brainai__")
    p_write = sub.add_parser("write-report", help="Écrit le rapport d'état sur disque.")
    p_write.add_argument("--tag", default="state")
    p_write.set_defaults(_method="__write__")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cp = _cp(args)
    method = getattr(args, "_method")

    if method == "__dashboard__":
        _out(dashboard_model(cp)); return 0
    if method == "__brainai__":
        _out(brainai_context(cp)); return 0
    if method == "__write__":
        _out(cp.write_state_report(tag=args.tag)); return 0

    result = getattr(cp, method)()
    _out(result)
    # code de sortie : 1 si une vérification/diagnostic échoue.
    if isinstance(result, dict) and result.get("ok") is False:
        return 1
    return 0


__all__ = ["main", "build_parser"]
