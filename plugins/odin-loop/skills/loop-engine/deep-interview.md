# Deep Interview Playbook (Huginn)

The engine loads this playbook when the current stage declares `interview.mode:
deep` in its loop YAML. It replaces "just follow the stage `prompt`" with a
**measured, convergence-driven interview**: enumerate the work as components,
score clarity every round, inject contrarian challenges, and stop only when
self-scored ambiguity falls to the configured threshold.

Odin-Loop has no code runtime — *you*, the engine LLM, are the runtime. So every
score here is an **honest self-assessment**, not a computed number. Write the
scores down anyway: a written ledger is what turns "deep enough" into a testable
gate instead of a vibe.

The stage `prompt` still matters — it supplies the **domain framing** (what this
particular interview is about, which dimensions to probe). This playbook supplies
the **procedure** that wraps that framing.

---

## Config (read from the stage's `interview:` block)

| Field         | Default                                   | Meaning                                             |
| ------------- | ----------------------------------------- | --------------------------------------------------- |
| `mode`        | —                                         | `deep` opts the stage into this playbook            |
| `threshold`   | `0.15`                                    | stop when run-level ambiguity ≤ this                |
| `challenges`  | `[contrarian@4, simplifier@6, ontologist@8]` | which contrarian probes fire, and at which round |
| `auto_assist` | `true`                                    | enable the auto-research / auto-answer sub-agents   |
| `dimensions`  | (defaults below)                          | weighted clarity dimensions; override only if the domain needs it |
| `hard_cap`    | `20`                                      | max rounds before proceeding with current clarity   |

**Default clarity dimensions (the scoring buckets):**

- **Greenfield** (no existing code to fit into):
  `goal 0.40 · constraints 0.30 · criteria 0.30`
- **Brownfield** (must fit existing code):
  `goal 0.35 · constraints 0.25 · criteria 0.25 · context 0.15`

A stage `prompt` may list more probing dimensions (the default loop lists eight).
Those are *what to ask about*; they each feed one of the buckets above (e.g.
"failure/error behavior" and "data/contracts" feed **criteria** + **constraints**).
Keep the buckets — they are what you score.

---

## Artifacts

| File               | Role                                                                 |
| ------------------ | ------------------------------------------------------------------- |
| `spec.md`          | the **deliverable** — the agreed spec (crystallized in Phase 4)      |
| `interview-log.md` | the **convergence ledger** — threshold, topology, per-round scores; the gate reads this |

Both live in the run dir (`.odin-loop/runs/<run-id>/`). Update `interview-log.md`
every round; rewrite `spec.md` as answers land.

---

## Phase 0 — Resolve the threshold

Read `interview.threshold` (default `0.15`). Write the ledger header:

```
# Interview Log — <task>   (deep interview)
ambiguity target: <threshold>   ·   dimensions: <bucket weights>   ·   mode: <greenfield|brownfield>
```

State the target out loud to the user in one line before the first question, so
the bar is shared: *"이 인터뷰는 ambiguity가 <threshold> 이하로 떨어지면 끝납니다."*

## Phase 1 — Initialize

1. **Greenfield vs brownfield.** Does the working tree already contain the code
   this work must fit into? If yes → brownfield (use the 4-bucket weights and the
   `context` dimension). If no → greenfield (3 buckets).
2. **Brownfield only — map first, ask second.** Spawn a **read-only** sub-agent
   (the `Explore` agent) to map the areas the work touches, so you never make the
   user rediscover facts the repo already states. Record the findings under a
   `## Context findings` section in the ledger and cite them (file:line) when you
   ask. Do **not** let the sub-agent edit anything.

## Round 0 — Topology gate (multi-component)

Before any scoring, decide **what the work is made of**.

1. Extract **1–6 top-level components** from the request. A component is a part
   that could have its own goal/criteria (e.g. for "ingest CSVs, normalize, a
   reviewer UI, and export reports" → `Ingestion`, `Normalization`, `Review UI`,
   `Export`).
2. Ask **one** confirmation question, listing the components:
   > 작업을 이렇게 나눠 봤습니다: [C1, C2, C3, …]. 맞나요? 빼거나 합치거나
   > 쪼개거나, 지금은 범위 밖으로 미룰 컴포넌트가 있나요?
3. Lock the result into the ledger. Each **active** component gets its own clarity
   slot; **deferred** components are recorded but not scored (and listed under
   `## Out of Scope` in `spec.md`).

```
## Topology   (status: confirmed @ <timestamp>)
- C1 <name>  — active
- C2 <name>  — active
- C3 <name>  — deferred (out of scope this run)
```

**The detailed component must not stand in for the vague ones.** If the user
described `Review UI` in depth but barely mentioned `Export`, Phase 2 still owes
`Export` enough questions to clear the threshold. Never let a well-described
sibling mask an under-described one.

## Phase 2 — Interview loop (convergence tracking)

Repeat until the **stop condition** holds. Each round:

**2a. Target the weakest dimension.** Across all *active* components, pick the
component+dimension with the lowest clarity (ties → the one blocking the most
downstream work). When >1 component is active, **rotate** targeting so you don't
overfit the most-described one.

**2b. Auto-research (optional, `auto_assist: true` + greenfield).** If the
targeted question is a research/architecture choice the user may not have a fixed
answer to, run the **auto-research sub-agent** (template below) for 2–3 ranked
candidate answers, and offer them as options in the question rather than asking
into a void.

**2c. Ask exactly one question,** contextualized so the user sees *why now*:

```
Round <n> | Component: <name> | Targeting: <dimension> | Ambiguity: <current>%
<the one question, in the user's language, with options when useful>
```

**2d. Auto-answer (optional, `auto_assist: true`).** If the user opts out, says
"you decide", or answers with explicit uncertainty, run the **auto-answer
sub-agent** (template below) for one conservative, reversible default. Carry it
forward as a stated assumption. **Clarity cap:** a dimension lifted *only* by an
auto-answer may not exceed `0.85` unless the sub-agent's confidence is `high` —
and if accepting it would cross the threshold, confirm with the user first.

**2e. Score.** Re-score each dimension 0–1 for the affected component(s):

- component ambiguity = `1 - Σ(clarity_d × weight_d)` over the buckets
- **run-level ambiguity = the MAX over active components** (the weakest component
  drives the gate — no component gets left fuzzy)
- **Ontology:** extract the key entities named so far (nouns → type: core /
  supporting / external, plus their fields/relations). Compare to last round's
  snapshot: `stability = (stable + renamed) / total`, where *renamed* = same type
  with >50% field overlap. Round 1 is `n/a` (all new).

**2f. Append a round entry** to `interview-log.md` (including the per-component
clarity scores) and persist the `interview` object to `state.json` — its four
contract fields `interview.threshold`, `interview.rounds`, `interview.ambiguity`,
and `interview.topology`, the set `/odin status` reads. Per-component clarity
stays in the ledger, not in `state.json`.

**2g. Soft caps.** Round ≥3: you may early-exit the moment the stop condition
holds. Round 10: warn the user you're 10 rounds in and offer to proceed with
current clarity. Round `hard_cap` (default 20): stop interviewing, record residual
ambiguity as `## Open Questions` risks, and proceed.

## Phase 3 — Challenge schedule (contrarian-perspective injection)

Parse `interview.challenges` (e.g. `contrarian@4`). When the round number first
reaches `N`, inject that challenge *before* the round's normal question — one
extra probe that attacks the emerging spec from a fixed angle:

| Challenge    | The probe                                                          | Fires            |
| ------------ | ----------------------------------------------------------------- | ---------------- |
| `contrarian` | "What if the opposite were true?" — name the assumption most likely to be wrong and test it. | at its round |
| `simplifier` | "What's the simplest version that still delivers the core value?" — try to cut a component or criterion. | at its round |
| `ontologist` | "What IS this, really?" — find the one core entity the whole spec orbits. | at its round, **only if** ambiguity > 0.3 |

Record each challenge and its outcome in the round's ledger entry (it often
*raises* ambiguity for a round by exposing a hidden assumption — that is the point).

## Phase 4 — Crystallize `spec.md`

When the stop condition holds, write the final spec. Keep the loop's fixed
section template and **add two sections**:

```
## Topology          # active components (+ deferred, marked out of scope)
## Convergence       # final per-dimension scores, run ambiguity, ontology stability trace
```

`spec.md` is the deliverable; `interview-log.md` is the evidence behind it.

## Stop condition  (this IS the gate)

All three must hold:

1. **run-level ambiguity ≤ `threshold`** (per `interview-log.md`), and
2. **every active topology component** has ≥1 observable, testable acceptance
   criterion in `spec.md`, and
3. **no unresolved blocking** item under `## Open Questions` (each is resolved or
   explicitly accepted as a non-blocking risk).

The stage gate (`ai+human`) checks exactly this against the two artifacts.

---

## Sub-agent template — auto-research (greenfield candidates)

Spawn a **read-only** sub-agent. It must not edit code, write files, or mutate
`.odin-loop/` state. Pass it: the run task, the confirmed topology, prior
decisions from the ledger, and the one targeted question. Ask for **only** this:

```
You are a read-only architect helping a deep interview answer ONE greenfield
question. Do not edit anything. Using only the inherited context + read-only repo
inspection, return 2–3 ranked, mutually distinct candidate answers that are
consistent with the confirmed constraints. For each: a one-line answer, why it
fits, its main risk/tradeoff, and confidence (high|medium|low). End with a
one-line recommendation and the single biggest remaining uncertainty the user must
still confirm. If you can't produce two defensible candidates, say so and name the
missing context — do not fabricate certainty.
```

Use the candidates as the *options* of question 2c. They never auto-decide.

## Sub-agent template — auto-answer (opt-out resolution)

Spawn a **read-only** sub-agent when the user opts out of a question. Same
read-only contract. Ask for one decisive, reversible default:

```
You are a read-only architect resolving ONE question a user opted out of. Do not
edit anything. Choose the most conservative answer that preserves the user's
intent and avoids irreversible assumptions. Return: one decisive answer phrased as
the assumption the interview should carry, 2–4 bullets of rationale citing
inherited context or repo facts, confidence (high|medium|low), and the explicit
remaining uncertainty (or null). If context is too thin for a defensible default,
return the safest reversible option, mark confidence low, and name what the user
must confirm before execution.
```

Apply the clarity cap from 2d to whatever this returns.

---

## Ledger format (`interview-log.md`)

```
# Interview Log — <task>   (deep interview)
ambiguity target: 0.15   ·   dimensions: goal .40 / constraints .30 / criteria .30   ·   mode: greenfield

## Topology   (status: confirmed @ 2026-06-15T10:02:00)
- C1 Ingestion      — active
- C2 Normalization  — active
- C3 Review UI      — active
- C4 Export         — active

## Context findings        # brownfield only; cite file:line
- ...

## Rounds
### Round 1 | targeting: goal · Ingestion
Q: ...
A: ...
scores (Ingestion): goal .55  constraints .40  criteria .30   → ambiguity .54
run ambiguity: .54   (worst: Ingestion)
ontology: 4 entities, stability n/a
challenge: —
auto-assist: auto-research → offered 3 candidates

### Round 4 | targeting: criteria · Export
challenge: contrarian → "do we even need PDF export?" → user confirmed CSV only
Q: ...
A: ...
scores (Export): goal .90  constraints .85  criteria .80   → ambiguity .15
run ambiguity: .19   (worst: Normalization)
ontology: 7 entities, stability 6/7 = .86

## Convergence trace
ambiguity:  1→.54  2→.41  3→.30  4→.19  5→.13   (target .15, reached @ round 5)
ontology stability:  n/a  .67  .83  .86  1.00
final per-component: Ingestion .12 · Normalization .14 · Review UI .10 · Export .13
```
