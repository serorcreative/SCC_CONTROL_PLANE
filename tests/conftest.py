"""Fixtures des tests du Control Plane.

Le Control Plane observe les composants SCC **réels** (API, Runtime, graphe) : les
tests sont des tests d'intégration déterministes (horodatage figé). Seul le
répertoire d'écriture (state) est redirigé vers un dossier temporaire.
"""

from __future__ import annotations

import pytest

from scc_control_plane.control_plane import ControlPlane
from scc_control_plane.core.config import load_config


@pytest.fixture
def config(tmp_path):
    cfg = load_config()
    cfg.state_dir = tmp_path / "state"
    return cfg


@pytest.fixture
def cp(config):
    return ControlPlane(config=config)
