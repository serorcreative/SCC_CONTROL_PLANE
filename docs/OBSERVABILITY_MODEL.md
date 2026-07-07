# Modèle d'observabilité du Control Plane

Le Control Plane produit quatre familles de sorties : **santé**, **métriques**,
**alertes**, **rapports**. Toutes sont des **données pures**, sérialisables,
déterministes.

## 1. Santé (`HealthState`)

| État | Sens |
|------|------|
| `ok` | composant/domaine présent et conforme |
| `degraded` | présent mais anomalie non bloquante (ex. job échoué) |
| `down` | absent ou injoignable |
| `unknown` | non déterminable |

Agrégation « pire état » : `ok < unknown < degraded < down`. L'état global du
système est le pire état de tous les domaines.

**Domaines supervisés** : les composants SCC (foundation, 5 moteurs, orchestrateur,
runtime, graph, decisions, meta_model) + les domaines transverses `api`,
`runtime_exec`, `agents`, `engines`.

## 2. Supervision par domaine

| Domaine | Source | Contenu |
|---------|--------|---------|
| **Système** | API | composants présents, graphe, readiness |
| **Runtime** | sonde | état, handlers, vetos, superviseur, self-check |
| **Jobs** | sonde | nombre, par statut, par confiance, garde-fou T3 |
| **Sessions** | sonde | nombre, acteur, autonomie, statut, jobs |
| **Événements** | sonde (`EventLog`) | nombre, par type, agrégats de gouvernance |
| **Agents** | API (catalogue + graphe) | total, répartition autonomie/confiance, orphelins sortants |
| **Moteurs** | API (statut + graphe) | présence, contrats produits/consommés, capacités implémentées |

## 3. Métriques d'activité

Agrégats **dérivés** (jamais mesurés à neuf), groupés par domaine :

- `system` : composants présents, verdict readiness, prérequis levés.
- `graph` : nœuds, arêtes, arêtes valides/invalides, orphelins.
- `catalog` : doctrines, capabilities, skills, workflows, agents, total.
- `runtime` : sessions, jobs, jobs réussis, événements, décisions/approbations de
  gouvernance, garde-fou T3.
- `agents` : total, orphelins sortants.
- `engines` : moteurs présents.

Deux formats : **groupé** (`groups`) et **plat** (`flat` : liste de
`{name, value, group}`, prête pour un tableau de bord).

## 4. Alertes (voir [`ALERTS.md`](ALERTS.md))

Émises par un **moteur de règles pures** à partir des observations. Chaque alerte :
`{id, code, severity, subject, message, timestamp, source}`. Journal ordonné,
déterministe, sérialisable en JSONL.

## 5. Diagnostics & auto-vérifications

- **Diagnostics** : batterie transverse (API joignable, graphe intègre, composants
  présents, readiness, Runtime sain, **preuve de déterminisme**). Renvoie un `Report`
  (`ok` global + checks).
- **Auto-vérification** : le Control Plane se contrôle lui-même (sources joignables,
  horloge déterministe configurée, répertoire d'état accessible, absence de LLM/réseau).

## 6. Rapports d'état

`state_report()` / `snapshot()` produisent le **document unique d'observabilité**
consolidant tout ce qui précède. `write_state_report(tag)` le persiste en **JSON**
(machine) + **Markdown** (humain), et dépose le **journal d'alertes** en JSONL sous
`state/` (jamais versionné).

## 7. Déterminisme

Toutes les sorties sont fonction pure des artefacts observés et de `as_of`. Deux
exécutions successives produisent des sorties **strictement identiques** — condition
d'un tableau de bord fiable et d'une supervision auditable.
