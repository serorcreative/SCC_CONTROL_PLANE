# Préparation du tableau de bord BrainAI (sans interface graphique)

> **Le Control Plane ne dessine rien.** Il fournit un **modèle de données** qu'un
> futur tableau de bord BrainAI mappera sur des widgets. C'est la préparation
> explicite exigée par le chantier — avec une frontière nette entre
> **observabilité** (ici) et **présentation** (plus tard).

## 1. Principe : séparer l'observation du rendu

Une couche de supervision robuste ne se couple pas à une technologie d'affichage.
Le Control Plane expose donc un **modèle de tableau de bord abstrait** : des
**panneaux** typés par un `kind` d'affichage, porteurs de leurs **données**. Le
rendu (terminal, web, application BrainAI…) est laissé au consommateur.

```python
from scc_control_plane import ControlPlane, dashboard_model
model = dashboard_model(ControlPlane())
# model["panels"] = liste de panneaux {id, title, kind, data}
```

## 2. Types de panneaux (`panel_kinds`)

| `kind` | Rendu attendu (côté consommateur) |
|--------|-----------------------------------|
| `status` | vignette d'état (badge couleur + chiffres clés) |
| `metric_grid` | grille de métriques (nom → valeur, par groupe) |
| `table` | tableau (colonnes + lignes) |
| `alert_list` | liste d'alertes triées par sévérité |

Le Control Plane **ne prescrit aucun style** : il nomme un type abstrait ; le
tableau de bord choisit le widget.

## 3. Panneaux fournis

`overview` (status) · `health_domains` (table) · `metrics` (metric_grid) ·
`runtime` (table) · `engines` (table) · `agents` (metric_grid) · `alerts`
(alert_list) · `diagnostics` (status).

## 4. Contexte BrainAI (read-only)

`brainai_context(cp)` fournit à une future couche BrainAI un **résumé
d'observabilité strictement en lecture** : santé globale, verdict de readiness,
alertes par sévérité, diagnostics OK, métriques. BrainAI *lit et se repère* ; il
**n'agit pas** depuis le Control Plane.

## 5. Continuité avec les autres préparations BrainAI

| Couche | Préparation BrainAI |
|--------|---------------------|
| Runtime (07) | port `SupervisorPort` (inerte) — plans/revues/décisions |
| API (08) | consommateur `ApiConsumer` — lecture + écriture gouvernée T3 |
| **Control Plane (09)** | **modèle de tableau de bord + contexte d'observabilité read-only** |

Ensemble, ces couches donnent à BrainAI, le jour venu : un **modèle du monde**
(graphe), une **façade d'action gouvernée** (API/Runtime) et une **vue de
supervision** (Control Plane) — sans qu'aucune n'ait à être réécrite.

## 6. Ce qui reste hors périmètre (volontairement)

- Aucune interface graphique, aucun serveur, aucun rendu HTML/JS.
- Aucun rafraîchissement temps réel réseau (le modèle est un instantané déterministe).

L'exposition d'un tableau de bord (transport, rendu, temps réel) fera l'objet d'un
chantier et d'un ADR dédiés — comme l'exposition HTTP de l'API.
