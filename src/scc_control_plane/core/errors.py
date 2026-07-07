"""Hiérarchie d'exceptions du Control Plane SCC."""

from __future__ import annotations


class ControlPlaneError(Exception):
    """Erreur de base de la couche de supervision."""


class ConfigError(ControlPlaneError):
    """Configuration absente, illisible ou invalide."""


class SourceUnavailable(ControlPlaneError):
    """Une source d'observation (API, Runtime) est introuvable/importable."""


__all__ = ["ControlPlaneError", "ConfigError", "SourceUnavailable"]
