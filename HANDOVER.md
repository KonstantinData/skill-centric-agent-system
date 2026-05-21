# Agent Handover — skill-centric-agent-system

**Datum:** 2026-05-21
**Branch:** `claude/recreate-venv-Gfz04`
**Repo:** `konstantindata/skill-centric-agent-system`
**Letzter Commit:** `b83a763`

---

## Kontext: Zwei Repos, eine Architekturentscheidung

Es gibt zwei Repos:

| Repo | Rolle |
|---|---|
| `konstantindata/multi-agent-intel-pipeline` | Produktiv-System. Liegt lokal als ZIP vor, kein GitHub-Schreibzugriff in dieser Session. |
| `konstantindata/skill-centric-agent-system` | Neues Architektur-Repo. Hier wird ADR-004 entwickelt, bevor es ins Pipeline-Repo integriert wird. |

Das Pipeline-Repo (`multi-agent-intel-pipeline`) ist ein Multi-Agent-System das
Meeting-Briefings zu Unternehmen erzeugt. Es läuft auf AG2 (AutoGen) GroupChats
mit 4 Departments × (Lead + Researcher + Critic + Judge + CodingSpecialist).
Alle Agents laufen heute **always-on**, unabhängig von der Qualität des
Researcher-Outputs. Das ist das Kostenproblem.

---

## Was in dieser Session entschieden und gebaut wurde

### Architekturentscheidung: Progressive Assurance

Ziel ist nicht "Agenten ersetzen", sondern **progressive assurance**:

1. `ResearchSkill` erzeugt `TaskArtifact` + Evidenzsignale.
2. Deterministischer Gate prüft: reicht das für Auto-Accept?
3. Critic läuft nur bei Risiko / Lücken / niedriger Evidenzqualität.
4. Judge läuft nur bei Ambiguität / Konflikten / kritischen Entscheidungen.
5. CodingSpecialist läuft nur bei Parsing-/Extraction-Problemen.

**Wichtig:** Confidence darf nicht vom LLM behauptet werden — sie muss aus
Evidenzsignalen berechnet werden (Quellanzahl, -mix, -aktualität,
Widersprüche, Pflichtfelder, Kritikalität, LTM-Pattern-Match).

### ADR-004: Progressive Assurance Shadow Mode

Status: **Draft** (noch nicht Proposed).

Kernentscheidung: Noch keine Agenten abschalten. Erst shadow mode messen.
Critic läuft weiter always-on; Gate berechnet *hypothetisch*, ob auto-accept
möglich gewesen wäre. Ergebnisse werden in `AssuranceShadowRecord` persistiert.

Dokument: `docs/runtime/adr-004-progressive-assurance.md`

### Implementierung

Alles in `src/orchestration/assurance.py` — dependency-light, kein AG2, keine
OpenAI-Imports, deterministisch testbar.

**Datenstrukturen:**

| Typ | Zweck |
|---|---|
| `TaskAssuranceSignals` | Evidenz-Signale (alle `float \| None`; LLM darf keine Werte setzen) |
| `TaskAssurancePolicy` | Pro-`task_key`-Gate-Konfiguration |
| `GateVerdict` | Deterministischer Output von `evaluate_gate()` |
| `CriticDeltaRecord` | Structured diff: was hat Critic tatsächlich geändert? |
| `AssuranceShadowRecord` | Wird an `TaskReviewArtifact` angehängt |

**Wichtige Konstanten:**

```python
LTM_BONUS_ENABLED = False   # bleibt False bis eval-Daten vorliegen
ASSURANCE_SCHEMA_VERSION = "1.0"
ASSURANCE_WEIGHTS_VERSION = "1.0"
```

**Gewichte (müssen bei Änderung ASSURANCE_WEIGHTS_VERSION bumpen):**

```python
required_fields_score:  0.30
source_mix_score:       0.20
contradiction_score:    0.20
source_freshness_score: 0.15
evidence_strength_score: 0.15
```

**Testabdeckung:** 65/65 Tests grün, `tests/architecture/test_assurance.py`.

---

## Bugs die in dieser Session gefunden und gefixt wurden

### Bug: `would_auto_accept` ignorierte `requires_judge`

`would_auto_accept` wurde vor der Judge-Auswertung berechnet. Ein Task mit
hohem Confidence-Score und aktiver Judge-Bedingung (z.B. `"conflict"`) konnte
`would_auto_accept=True` zurückgeben, obwohl Judge erforderlich war.

**Fix:**
```python
would_auto_accept = (
    policy.auto_accept_allowed
    and not requires_critic
    and not requires_judge      # ← war vorher nicht enthalten
)
```

Test-Klasse: `TestAutoAcceptRequiresJudgeClear`.

---

## Explizite Design-Entscheidungen (nicht ändern ohne ADR-Update)

1. **`float | None` für alle Signale** — `None` bedeutet "nicht erkennbar aus
   dem Artifact", nicht "null". `_resolve_score(None)` → 0.5 (neutral).
   Contradiction `None` triggert **nicht** den "conflict" Judge-Condition.

2. **`contradiction_score` nicht auf 1.0 defaulten** — nur setzen wenn
   strukturierte Widerspruchserkennung im `TaskArtifact` vorhanden ist.

3. **`critical` als expliziter Branch** — nicht als Delta (+1.0), weil
   `min(1.0, threshold + 1.0) = 1.0` und `confidence=1.0 < 1.0 = False` sonst
   durchrutscht. Expliziter Check verhindert Edge Case.

4. **LTM-Bonus deaktiviert** — `LTM_BONUS_ENABLED=False`. Nur aktivieren,
   wenn `ltm_pattern_precision` aus gemessenen Recall-Daten kommt (nicht aus
   einem unkalibriertem Matching-Score).

5. **`ltm_precision_floor` per Policy** — erlaubt department-spezifisches
   Tuning. Global-Default: 0.70.

6. **`escalation_reason: tuple[str, ...]`** — nicht `str | None`, weil
   mehrere Runtime-Conditions (max_retries + ambiguity) unabhängig erfassbar
   sein müssen.

7. **`_compute_confidence` gibt `(score, ltm_bonus_applied)` zurück** —
   beide landen im `GateVerdict` für selbstbeschreibende Verdicts.

---

## Was noch nicht gemacht wurde (explizit offen gelassen)

| Offen | Warum |
|---|---|
| Integration in `src/orchestration/contracts.py` (Pipeline-Repo) | ADR-004 muss erst Proposed/Accepted sein |
| `AssuranceShadowRecord` an `TaskReviewArtifact` anhängen | Gleiche Bedingung |
| `actual_critic_delta` befüllen (Diff-Wire-Up) | Runtime-Impl fehlt; Feld ist `None`-safe |
| `minimum_source_count` im Gate auswerten | Feld existiert in Policy, Gate ignoriert es noch |
| Researcher-Logik konsolidieren (4 Copies → 1 Skill) | Non-Goal von ADR-004, eigenes ADR |
| LTM-Bonus aktivieren | Erst nach messbarer Precision aus Eval-Daten |
| ADR-004 Status von Draft → Proposed | Entscheidung liegt beim Owner |

---

## Nächste konkrete Schritte (empfohlen)

**1. Shadow-Mode-Messung vorbereiten**
Definiere Policies für die häufigsten `task_key`-Werte im Pipeline-Repo
(z.B. `company_overview`, `market_analysis`, `contact_discovery`). Wähle
realistische `critic_required_below`-Schwellen basierend auf bisherigen Runs.

**2. `actual_critic_delta` verdrahten**
In `src/agents/critic.py` (Pipeline-Repo) nach dem Critic-Run eine
`CriticDeltaRecord`-Instanz bauen und in `AssuranceShadowRecord` setzen.
Minimal: `changed_outcome`, `rejected_points_count`, `would_have_blocked_auto_accept`.

**3. Shadow-Daten auswerten**
Nach N Runs: Wie viele Tasks hätten auto-accepted? Bei wie vielen hätte
`would_have_blocked_auto_accept=True` einen echten Qualitätsverlust bedeutet?

**4. ADR-004 auf Proposed setzen** (wenn Shadow-Messung stabil läuft)

---

## Umgebung

```
Repo:    konstantindata/skill-centric-agent-system
Branch:  claude/recreate-venv-Gfz04
Python:  3.11.15 (venv im Repo-Root)
Tests:   venv/bin/pytest tests/architecture/test_assurance.py
Plattform: Remote Cloud Container (Linux); Entwicklung lokal auf Windows
```

Der `multi-agent-intel-pipeline`-Code liegt unter
`/tmp/multi-agent-intel-pipeline/multi-agent-intel-pipeline-main/`
(aus ZIP entpackt, nicht committed).

---

## Referenz-Dateien

```
docs/runtime/adr-004-progressive-assurance.md   ← ADR (Draft)
src/orchestration/assurance.py                   ← Implementierung
tests/architecture/test_assurance.py             ← 65 Tests
```

Verwandte ADRs im Pipeline-Repo:
- `docs/runtime/adr-001-runtime-step-contract.md`
- `docs/runtime/adr-003-reasoning-profiles.md` (StepReasoningPolicy — ADR-004 koppelt daran)
