"""Noyau du Control Plane : configuration, erreurs, modèle d'observabilité."""

from __future__ import annotations

from scc_control_plane.core.config import ControlPlaneConfig, load_config
from scc_control_plane.core.errors import ConfigError, ControlPlaneError, SourceUnavailable
from scc_control_plane.core.model import (
    Alert,
    Check,
    ComponentHealth,
    HealthState,
    Metric,
    Report,
    Severity,
    worst,
)

__all__ = [
    "ControlPlaneConfig",
    "load_config",
    "ControlPlaneError",
    "ConfigError",
    "SourceUnavailable",
    "HealthState",
    "worst",
    "Severity",
    "ComponentHealth",
    "Alert",
    "Metric",
    "Check",
    "Report",
]
