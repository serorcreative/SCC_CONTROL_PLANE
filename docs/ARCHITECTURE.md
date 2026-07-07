# Architecture du Control Plane SCC

## 1. Position dans SCC

Le Control Plane est la couche de **supervision/observabilité** (09). Il se place
**au-dessus** de tout l'écosystème et n'en **observe** que l'état — il ne pilote pas,
ne modifie pas, n'expose pas de services externes (c'est le rôle de l'API).

```
        (futur) Tableau de bord BrainAI  ── mappe le modèle de panneaux (données)
                 │  dashboard_model() / brainai_context()  (aucune GUI ici)
   ▶ CONTROL PLANE (09)  ── ControlPlane : santé · supervision · métriques · alertes · diagnostics
                 │
      ┌──────────┴───────────┐
   ApiSource            RuntimeProbe
   (lecture via         (sonde déterministe via
    scc_api.dispatch)    EventLog.subscribe + horloge injectée)
        │                      │
     API (08)             Runtime (07)
        │                      │
   Graphe · Catalogues · Readiness   Sessions · Jobs · Événements · Gouvernance
```

## 2. Principe : observer sans dupliquer

La règle du chantier — *ne jamais dupliquer une responsabilité existante* — dicte
l'architecture :

- **Lecture de l'écosystème** (inventaire, graphe, readiness, santé de base,
  catalogues) → **réutilise l'API** via `ApiSource.call("<operation>")`. Le Control
  Plane ne relit pas les artefacts lui-même.
- **Exécution / gouvernance** (sessions, jobs, événements, T3, vetos) → **réutilise
  le Runtime** via une **sonde** qui s'abonne au `EventLog` et lit `state.snapshot()`.
- **Ce qui n'existait pas** (santé consolidée, métriques d'activité, journal
  d'alertes, diagnostics transverses, auto-vérifications, rapports d'état) → **ajouté
  ici**, et nulle part ailleurs.

Aucune ligne de l'API, du Runtime ou d'un moteur n'est modifiée : le Control Plane
n'utilise que des **points d'extension publics**.

## 3. Points d'extension utilisés (aucune modification)

| Extension | Fournie par | Usage |
|-----------|-------------|-------|
| `SccApi.dispatch(op, params)` | API (08) | lecture de l'état, du graphe, des catalogues |
| `EventLog.subscribe(cb)` | Runtime (07) | supervision des événements en direct |
| `RuntimeEngine(clock=…, id_factory=…, supervisor=…)` | Runtime (07) | sonde **déterministe** |
| `RuntimeEngine.state.snapshot()` / `self_check()` | Runtime (07) | supervision jobs/sessions + santé |

## 4. Couches internes

```
core/        config (as_of figé) · errors · model (HealthState, Severity, Alert, Report)
sources/     ApiSource (API) · RuntimeProbe (Runtime, déterministe)
monitors     SystemMonitor · RuntimeMonitor · AgentsMonitor · EnginesMonitor
metrics      MetricsCollector (agrégats par domaine)
alerts       AlertJournal + moteur de règles pures
diagnostics  batterie transverse (+ preuve de déterminisme)
control_plane  ControlPlane (façade unique)
dashboard    dashboard_model() / brainai_context() (données, pas de GUI)
cli          scc-control
```

## 5. Déterminisme (garantie de conception)

- **Horodatage figé** : `config.as_of` est l'unique source de temps ; aucune horloge
  murale n'est lue. Alertes et rapports en héritent.
- **Sonde Runtime déterministe** : injection de `FixedClock(as_of)` +
  `SequentialFactory` → identifiants de jobs/événements et horodatages **rejouables**.
- **Règles et métriques pures** : mêmes observations ⇒ mêmes alertes, mêmes chiffres.
- **Preuve automatisée** : le diagnostic `runtime_deterministic` compare deux sondes
  indépendantes et exige une empreinte identique. Deux `snapshot` successifs sont
  **byte-for-byte identiques** (vérifié).

## 6. Santé consolidée (rollup)

Chaque domaine produit une `ComponentHealth` (`ok`/`degraded`/`down`/`unknown`).
L'état global est le **pire** état observé (`worst()`), selon l'ordre
`ok < unknown < degraded < down`. Un composant absent ⇒ `down` ⇒ dégrade l'ensemble.

## 7. Invariants tenus

| Invariant | Comment |
|-----------|---------|
| Aucun moteur modifié | observation seule |
| Ni Runtime ni API modifiés (hors extensions prévues) | `dispatch`, `EventLog.subscribe`, injection d'horloge |
| Aucun LLM / réseau | aucun client instancié ; stdlib pur |
| Aucune dépendance externe | stdlib uniquement |
| Déterminisme total | `as_of` figé + sonde déterministe + règles pures |
| Pas de GUI | le tableau de bord est un **modèle de données** |
