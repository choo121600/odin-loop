# Odin-Loop — Design

**English** | [한국어](design.ko.md)

How Odin-Loop is put together, and why. The one idea everything else follows
from: **the loop is data, not code.**

## The loop is data

A workflow loop is a YAML file. The engine reads that file and executes whatever
stages it declares — it never hardcodes a particular workflow. Change the YAML
and you change the process; no engine code changes. This is what lets you ship a
strong default loop *and* let users author their own with `/odin-loop:odin new`, or have
Muninn propose edits with `/odin-loop:odin refine`.

The built-in loop ([`spec-harness-tdd.yaml`](../plugins/odin-loop/loops/spec-harness-tdd.yaml))
is the reference for the schema; its header documents every field.

## The cast (myth → architecture)

| Myth | Role in Odin-Loop |
| --- | --- |
| **Odin** | the engine that drives the loop |
| **Huginn** ("thought") | the deep-**interview** stage — turns intent into testable criteria |
| **Muninn** ("memory") | the session-mining refiner (`/odin-loop:odin refine`) |
| **Gungnir** | the spear that never misses — the **harness-verify** gate |

Huginn and Gungnir are *stages inside a loop*; Muninn is the *outer* loop that
edits the loop itself.

## Stages and gates

Each stage has a `goal`, a `prompt` the engine follows, optional `consumes` /
`produces` artifact hints, an optional `agent` execution context, and a **gate**
— the condition to advance:

```yaml
- id: review
  gate:
    mode: ai+human        # ai = engine judges & auto-advances · ai+human = pause for approval
    check: <a testable assertion>
    on_fail: implement        # where to jump when the gate fails (omit = retry this stage)
```

- `mode: ai` — the engine judges the `check` honestly and advances automatically.
- `mode: ai+human` — the engine judges, then **pauses** for your approval.
- `on_fail` — the stage id to loop back to on failure.
- `agent` — *who* runs the stage. Omit it (or `inline`) to run it in the engine
  itself; `fresh` runs it in a clean-room sub-agent with no prior conversation
  context, for an independent review/audit the rest of the run can't bias (it sees
  only the stage's `consumes` artifacts). `agent` can also name one of five
  reusable **roles** — `explore` (read-only scout, fresh), `planner` (spec → build
  plan, inline), `executor` (harness/implement/test, inline), `critic` (adversarial
  verify, fresh), `reviewer` (clean review, fresh) — each a persona shipped at
  `plugins/odin-loop/agents/<role>.md`. A role is a bare string for its default
  context, or `{ role, fresh }` to override it. The role governs *how* the worker
  behaves; the stage's `goal`/`gate`/`prompt`/`produces` stay authoritative.
- A global **`max_iterations`** caps gate failures (loopbacks) so a failing loop
  reports instead of spinning forever; happy-path runs are not counted.

Gates are meant to be judged honestly: a gate that rubber-stamps proves nothing.

## Deep interview (Huginn)

A requirement-gathering stage can opt into the **deep-interview playbook** by
declaring `interview.mode: deep`. The playbook
([`skills/loop-engine/deep-interview.md`](../plugins/odin-loop/skills/loop-engine/deep-interview.md))
turns the interview from "ask until it feels done" into a measured loop:

- **Topology** — Round 0 enumerates the work as 1–6 components and confirms them
  with you, so a well-described part can't mask a vague sibling.
- **Convergence** — each round self-scores clarity per dimension and records
  `ambiguity = 1 − Σ(clarity × weight)` into `interview-log.md`; the gate advances
  only when ambiguity ≤ the configured `threshold`. Odin-Loop has no code runtime,
  so these scores are an **honest self-assessment by the engine, not a computed
  metric** — the value is the written, inspectable trail, not false precision.
- **Challenges** — at scheduled rounds it injects contrarian / simplifier /
  ontologist probes that attack the emerging spec from a fixed angle.
- **Auto-assist** — read-only sub-agents propose ranked candidate answers
  (greenfield) or resolve a question you opt out of, without ever deciding for you.

The stage `prompt` still supplies the domain framing; the playbook supplies the
procedure. `spec.md` is the deliverable; `interview-log.md` is the evidence the
gate reads.

## Run state (`state.json`)

Each run persists its state so it can be resumed across sessions. The key fields:

```json
{
  "run_id": "20260614-143501-spec-harness-tdd",
  "loop": "spec-harness-tdd",
  "status": "running | awaiting_approval | done | failed",
  "current_stage": "interview",
  "iterations": { "implement": 2, "test": 2 },
  "total_iterations": 4,
  "max_iterations": 15,
  "interview": { "threshold": 0.15, "rounds": 4, "ambiguity": 0.13, "topology": ["Ingestion", "Export"] },
  "history": [
    { "stage": "interview", "result": "pass", "gate": "approved", "at": "..." },
    { "stage": "review", "result": "pass", "gate": "approved", "at": "...", "agent": "fresh" }
  ]
}
```

`current_stage` is where the run resumes; `history` is the audit trail of gate
decisions; `total_iterations` is checked against `max_iterations` on every loopback.
The optional `interview` object appears only for a deep-interview stage and mirrors
its convergence (see [Deep interview](#deep-interview-huginn)).

## Where artifacts live

| Thing | Path |
| --- | --- |
| Built-in loops | `plugins/odin-loop/loops/*.yaml` |
| Custom loops | `.odin-loop/loops/*.yaml` (in your project) |
| Run state & docs | `.odin-loop/runs/<run-id>/` |
| Run harness & stubs | `.odin-loop/runs/<run-id>/harness/` (gitignored) |
| Shipped deliverable | the real project tree (`src/`, committed tests, docs) |

`.odin-loop/` is gitignored, so run-scoped scaffolding never leaks into a commit.

## Loop resolution order

When a loop name is referenced, the engine resolves it by checking the **project**
`.odin-loop/loops/` first, then the **built-in** `plugins/odin-loop/loops/`. So a
project can override or add loops without touching the plugin.

---

See also: [Features](features.md) · [Scenarios](scenarios.md) · [← README](../README.md)
