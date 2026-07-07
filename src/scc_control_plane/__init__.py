"""SCC Control Plane — couche officielle de supervision et d'observabilité.

Le Control Plane **observe** l'ensemble de Seror Créative Core sans rien y modifier.
Il réutilise l'API (`08_API`) comme façade de lecture et le Runtime (`07_RUNTIME`)
via ses points d'extension publics (journal d'événements, horloge injectable), puis
ajoute ce qui manquait : santé consolidée, supervision (Runtime/jobs/sessions/
agents/moteurs/événements), métriques, journal d'alertes, diagnostics,
auto-vérifications et rapports d'état.

Principes : aucun moteur/Runtime/API modifié ; aucun LLM ; aucun réseau ; stdlib
pur ; **déterminisme total** ; préparation explicite d'un tableau de bord BrainAI
(modèle de données, sans interface graphique).
"""

from __future__ import annotations

__version__ = "1.0.0"

from scc_control_plane.control_plane import ControlPlane
from scc_control_plane.core.config import ControlPlaneConfig, load_config
from scc_control_plane.dashboard import brainai_context, dashboard_model

__all__ = [
    "__version__",
    "ControlPlane",
    "ControlPlaneConfig",
    "load_config",
    "dashboard_model",
    "brainai_context",
]
