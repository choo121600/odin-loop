# Odin-Loop — Design

**English** | [한국어](design.ko.md)

How Odin-Loop is put together, and why. The one idea everything else follows
from: **the loop is data, not code.**

## The loop is data

A workflow loop is a YAML file. The engine reads that file and executes whatever
stages it declares — it never hardcodes a particular workflow. Change the YAML
and you change the process; no engine code changes. This is what lets you ship a
strong default loop *and* let users author their own with `/odin new`, or have
Muninn propose edits with `/odin refine`.

The built-in loop ([`spec-harness-tdd.yaml`](../plugins/odin-loop/loops/spec-harness-tdd.yaml))
is the reference for the schema; its header documents every field.

## The cast (myth → architecture)

| Myth | Role in Odin-Loop |
| --- | --- |
| **Odin** | the engine that drives the loop |
| **Huginn** ("thought") | the deep-**interview** stage — turns intent into testable criteria |
| **Muninn** ("memory") | the session-mining refiner (`/odin refine`) |
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
- `agent: fresh` — run the stage in a clean-room sub-agent with no prior
  conversation context, for an independent review/audit the rest of the run can't
  bias (it sees only the stage's `consumes` artifacts). Omit it, or `inline`, to
  run the stage in the engine itself.
- A global **`max_iterations`** caps gate failures (loopbacks) so a failing loop
  reports instead of spinning forever; happy-path runs are not counted.

Gates are meant to be judged honestly: a gate that rubber-stamps proves nothing.

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
  "history": [
    { "stage": "interview", "result": "pass", "gate": "approved", "at": "..." },
    { "stage": "review", "result": "pass", "gate": "approved", "at": "...", "agent": "fresh" }
  ]
}
```

`current_stage` is where the run resumes; `history` is the audit trail of gate
decisions; `total_iterations` is checked against `max_iterations` on every loopback.

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
