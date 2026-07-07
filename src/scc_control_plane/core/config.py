"""Configuration du Control Plane (JSON, sans dépendance).

Le Control Plane est une couche d'**observation** : il localise les composants SCC
déjà construits (l'API `08_API`, le Runtime `07_RUNTIME`) et les artefacts, mais ne
possède ni ne modifie aucun d'eux.

Déterminisme : ``as_of`` fige l'horodatage de toutes les observations, alertes et
rapports (aucune horloge murale n'est jamais lue).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from scc_control_plane.core.errors import ConfigError

CP_ROOT = Path(__file__).resolve().parents[3]            # .../09_CONTROL_PLANE
DEFAULT_SCC_ROOT = CP_ROOT.parent                         # .../01_CCSC
DEFAULT_CONFIG_PATH = CP_ROOT / "config" / "control_plane.json"

# Horodatage déterministe par défaut (aligné sur les chantiers SCC).
DEFAULT_AS_OF = "2026-07-06T00:00:00+00:00"


@dataclass
class ControlPlaneConfig:
    """Emplacements observés et paramètres déterministes."""

    cp_root: Path = CP_ROOT
    scc_root: Path = DEFAULT_SCC_ROOT
    state_dir: Path = CP_ROOT / "state"
    as_of: str = DEFAULT_AS_OF
    demo_query: str = "architecture"
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def api_src(self) -> Path:
        return self.scc_root / "08_API" / "src"

    @property
    def runtime_src(self) -> Path:
        return self.scc_root / "07_RUNTIME" / "src"

    def ensure_directories(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cp_root": str(self.cp_root),
            "scc_root": str(self.scc_root),
            "state_dir": str(self.state_dir),
            "as_of": self.as_of,
            "demo_query": self.demo_query,
        }


def _resolve(base: Path, value: str) -> Path:
    p = Path(value).expanduser()
    return p if p.is_absolute() else (base / p).resolve()


def load_config(path: Optional[Path] = None) -> ControlPlaneConfig:
    config = ControlPlaneConfig()
    target = Path(path) if path else DEFAULT_CONFIG_PATH
    if not target.exists():
        if path is not None:
            raise ConfigError(f"Configuration introuvable : {target}")
        return config
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Configuration illisible ({target}) : {exc}") from exc

    base = config.cp_root
    if "scc_root" in raw:
        config.scc_root = _resolve(base, raw["scc_root"])
    paths = raw.get("paths", {})
    if "state_dir" in paths:
        config.state_dir = _resolve(base, paths["state_dir"])
    config.as_of = str(raw.get("as_of", DEFAULT_AS_OF))
    config.demo_query = str(raw.get("demo_query", config.demo_query))
    config.extra = dict(raw.get("extra", {}))
    return config


__all__ = ["CP_ROOT", "DEFAULT_SCC_ROOT", "DEFAULT_AS_OF", "ControlPlaneConfig", "load_config"]
