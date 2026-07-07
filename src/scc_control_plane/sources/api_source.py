"""Source d'observation : l'API SCC (réutilisée, jamais dupliquée).

Le Control Plane ne relit pas les artefacts lui-même : il **consomme l'API**
(`08_API`) via son contrat public ``dispatch``. L'API est localisée dynamiquement
(ajout de son ``src/`` à ``sys.path``), sans être modifiée.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from scc_control_plane.core.config import ControlPlaneConfig
from scc_control_plane.core.errors import SourceUnavailable


class ApiSource:
    """Adaptateur mince au-dessus de ``scc_api.SccApi`` (lecture)."""

    def __init__(self, config: ControlPlaneConfig):
        self._config = config
        self._api = None

    def _ensure(self):
        if self._api is not None:
            return self._api
        src = self._config.api_src
        if not src.exists():
            raise SourceUnavailable(f"API SCC introuvable : {src}")
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
        try:
            mod = importlib.import_module("scc_api")
        except ImportError as exc:  # pragma: no cover - dépend de l'environnement
            raise SourceUnavailable(f"Import de l'API impossible : {exc}") from exc
        self._api = mod.SccApi()
        return self._api

    @property
    def available(self) -> bool:
        try:
            self._ensure()
            return True
        except SourceUnavailable:
            return False

    def call(self, operation: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Renvoie l'enveloppe de réponse brute de l'API (dict)."""
        api = self._ensure()
        return api.dispatch(operation, params or {}).to_dict()

    def data(self, operation: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Renvoie le ``data`` d'une opération, ou lève si l'opération a échoué."""
        env = self.call(operation, params)
        if not env.get("ok"):
            raise SourceUnavailable(
                f"L'opération API '{operation}' a échoué : {env.get('error')}"
            )
        return env.get("data")

    # -- raccourcis de lecture ------------------------------------------ #
    def status(self) -> Dict[str, Any]:
        return self.data("system.status")

    def health(self) -> Dict[str, Any]:
        return self.data("system.health")

    def inventory(self) -> Dict[str, Any]:
        return self.data("system.inventory")

    def readiness(self) -> Dict[str, Any]:
        return self.data("system.readiness")

    def graph_summary(self) -> Dict[str, Any]:
        return self.data("graph.summary")

    def runtime_info(self) -> Dict[str, Any]:
        return self.data("runtime.info")

    def agents(self) -> list:
        return self.data("catalog.agents")

    def reports(self) -> list:
        return self.data("reports.list")


__all__ = ["ApiSource"]
