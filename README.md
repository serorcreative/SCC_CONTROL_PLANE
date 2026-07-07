# SCC Control Plane

**Couche officielle de supervision et d'observabilité de Seror Créative Core.**

Le Control Plane **observe l'ensemble de SCC sans rien y modifier**. Il **réutilise**
l'API (`08_API`) comme façade de lecture et le Runtime (`07_RUNTIME`) via ses points
d'extension publics (journal d'événements, horloge injectable), puis **ajoute** ce
qui manquait : santé consolidée, supervision, métriques, alertes, diagnostics,
auto-vérifications et rapports d'état.

> **Aucun moteur, Runtime ou API modifié. Aucun LLM. Aucun réseau. Stdlib pur.
> Déterminisme total** (horodatage figé `as_of`). Préparation explicite d'un
> tableau de bord BrainAI — **sans interface graphique**.

## Installation

```bash
cd 09_CONTROL_PLANE
python -m pip install -e .        # expose la commande `scc-control`
```

Aucune dépendance externe.

## Utilisation (CLI)

```bash
scc-control state          # état global du système
scc-control health         # santé consolidée (rollup de tous les domaines)
scc-control components     # santé des composants
scc-control runtime        # supervision Runtime
scc-control jobs           # supervision des jobs
scc-control sessions       # supervision des sessions
scc-control events         # supervision des événements
scc-control agents         # supervision des agents
scc-control engines        # supervision des moteurs
scc-control metrics        # métriques d'activité
scc-control alerts         # journal des alertes
scc-control diagnostics    # diagnostics transverses (dont preuve de déterminisme)
scc-control self-check     # auto-vérification de la couche
scc-control report         # rapport d'état consolidé
scc-control snapshot       # instantané complet (base tableau de bord)
scc-control dashboard      # modèle de tableau de bord (données, sans GUI)
scc-control brainai-context# contexte read-only pour BrainAI
scc-control write-report   # écrit JSON + Markdown + journal d'alertes dans state/
```

## Utilisation (Python)

```python
from scc_control_plane import ControlPlane, dashboard_model

cp = ControlPlane()
print(cp.health()["overall"])          # "ok"
print(cp.diagnostics()["ok"])          # True
panels = dashboard_model(cp)["panels"] # modèle de tableau de bord (données pures)
```

## Ce que la couche fournit

État global · santé des composants · supervision Runtime / Jobs / Sessions / Agents
/ Moteurs / Événements · métriques d'activité · journal des alertes · diagnostics ·
auto-vérifications · rapports d'état. Détails :
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) ·
[`docs/OBSERVABILITY_MODEL.md`](docs/OBSERVABILITY_MODEL.md) ·
[`docs/ALERTS.md`](docs/ALERTS.md) ·
[`docs/BRAINAI_DASHBOARD.md`](docs/BRAINAI_DASHBOARD.md).

## Tests

```bash
python -m pytest -q      # 24 tests (intégration déterministe sur composants réels)
```

## Non-duplication

Le Control Plane **ne réimplémente rien** : l'inventaire, la lecture du graphe, la
readiness et la santé de base viennent de l'**API** ; les jobs/sessions/événements
et la gouvernance viennent du **Runtime**. La couche ajoute uniquement la
**supervision** (agrégation, santé consolidée, métriques, alertes, diagnostics).
