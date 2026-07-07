# Journal des alertes — moteur de règles

Les alertes sont émises par des **règles pures et déterministes** appliquées aux
observations. Elles **signalent des écarts observables**, elles ne portent aucun
jugement sur l'architecture (qui relève des Doctrines et des ADR).

## 1. Sévérités

| Sévérité | Sens |
|----------|------|
| `critical` | anomalie bloquante (ex. readiness NOT READY) |
| `error` | anomalie à corriger (ex. arête de graphe invalide, job échoué) |
| `warning` | écart non bloquant (ex. orphelins de graphe) |
| `info` | fait notable, souvent sain (ex. garde-fou T3 actif) |

Tri du journal : sévérité décroissante puis `id`.

## 2. Règles

| Code | Sévérité | Déclencheur |
|------|----------|-------------|
| `component_missing` | error | un composant SCC attendu est absent (`down`) |
| `graph_invalid_edges` | error | ≥ 1 relation hors grammaire dans le graphe |
| `graph_orphans` | warning | ≥ 1 nœud orphelin dans le graphe |
| `readiness_not_ready` | critical | verdict de readiness ≠ READY* |
| `readiness_warnings` | info | verdict READY WITH WARNINGS |
| `prerequisites_open` | warning | un prérequis de readiness reste ouvert |
| `runtime_jobs_failed` | error | ≥ 1 job Runtime en échec |
| `t3_guardrail_active` | info | action T3 bloquée puis validée humainement (gouvernance saine) |
| `agent_out_orphan` | info | un agent n'a aucune relation sortante dans le graphe |

## 3. Format d'une alerte

```json
{
  "id": "alert:graph_orphans:graph",
  "code": "graph_orphans",
  "severity": "warning",
  "subject": "graph",
  "message": "4 nœud(s) orphelin(s) dans le graphe.",
  "timestamp": "2026-07-06T00:00:00+00:00",
  "source": "control_plane"
}
```

L'**identifiant est déterministe** (`alert:<code>:<sujet>`) : une même situation
produit toujours la même alerte, sans doublon. L'horodatage est figé (`as_of`).

## 4. État actuel (instantané de référence)

Sur l'écosystème SCC tel qu'observé, le journal contient **4 alertes**, toutes
attendues et bénignes :

- `warning graph_orphans` — 4 documents de spécification/rapport non liés par
  wikilink (connus, documentés au chantier SCC-GRAPH-001) ;
- `info agent_out_orphan` — `SCC-AGENT-0020` (Superviseur BrainAI), rôle
  supervisant sans relation sortante (cohérent) ;
- `info readiness_warnings` — READY WITH WARNINGS ;
- `info t3_guardrail_active` — garde-fou T3 observé (preuve de gouvernance active).

**Aucune alerte `error` ni `critical`** : le système est sain.

## 5. Persistance

`write-report` dépose le journal courant en JSONL sous `state/<tag>_alerts.jsonl`
(jamais versionné). Le journal est **rejoué à l'identique** à chaque exécution.
