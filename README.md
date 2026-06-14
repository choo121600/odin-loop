# Odin-Loop

**English** | [한국어](README.ko.md)

> Author, run, and refine your own AI dev workflow *loops* — as editable data.

Most "AI dev workflow" tools hand you **one fixed loop**. Odin-Loop treats the
loop itself as a first-class, editable artifact: a YAML file the engine reads and
executes. It ships with a strong default loop, and lets you build and refine your
own with `/odin new`.

```
deep interview → harness design → harness verify → implement → test
   (Huginn)                          (Gungnir)
```

The names come from the myth, and they map onto the architecture:

| Myth | Role | In Odin-Loop |
| --- | --- | --- |
| **Odin** | the seeker of wisdom who drives the hunt | the engine that drives the loop |
| **Huginn** ("thought") | raven of reasoning | the deep-interview stage |
| **Muninn** ("memory") | raven of memory | session-mining refiner (`/odin refine`) |
| **Gungnir** | the spear that never misses | the harness-verification gate |

## Why the default loop is shaped this way

- **Deep interview first** — most AI coding failures are intent failures, not
  coding failures. The interview turns a vague request into *testable acceptance
  criteria* before any code is written.
- **Harness before implementation** — the criteria become executable tests, so
  "done" has an objective definition.
- **Verify the harness itself (Gungnir)** — the step most tools skip. A test that
  always passes proves nothing. We run a deliberately-wrong stub and require at
  least one test to *fail* — proving the harness has teeth.
- **Then implement and test** — implement against the verified harness; loop back
  on failure, bounded by a `max_iterations` cap.

## Install

```
/plugin marketplace add choo121600/odin-loop
/plugin install odin-loop@odin-loop
```

## Usage

```
/odin run            # start or continue a run (pauses at human-approval gates)
/odin step <stage>   # re-run one specific stage
/odin status         # show the active run's state
/odin list           # list available loops
/odin new            # author your own loop, by interview
/odin refine [loop]  # analyze past work and propose loop edits (Muninn)
```

### Hybrid execution

`/odin run` drives the loop automatically, but **stops at `ai+human` gates** so
you stay in control. Approve a paused stage by running `/odin run` again; or just
type feedback to revise that stage and re-gate.

### Muninn — the self-refining loop

`/odin refine` mines your Odin-Loop run history and raw Claude Code session
transcripts to find where you skip stages, re-work, or loop back — then proposes
**concrete edits to your loop's YAML** (e.g. "your `implement` stage loops back a
lot → tighten the `interview` gate"). A bundled analyzer extracts aggregate
signals only (never message content), and **nothing is applied without your
approval** — run `/odin refine apply` to accept. The loop learns from how you
actually work.

## Loops are data

A loop is a YAML file (see [`plugins/odin-loop/loops/spec-harness-tdd.yaml`](plugins/odin-loop/loops/spec-harness-tdd.yaml)
for the fully-commented schema). The essentials:

```yaml
name: my-loop
version: 1
max_iterations: 12
stages:
  - id: design
    goal: ...
    gate:
      mode: ai+human        # ai = auto-advance · ai+human = pause for approval
      check: <testable assertion to advance>
      on_fail: <stage id to loop back to>   # optional
```

Built-in loops live in `loops/`; your custom loops live in
`.odin-loop/loops/` in your project. Run state lives in `.odin-loop/runs/`.

## Status

`v0.2.0` — engine + default loop + custom-loop authoring + Muninn (`/odin refine`)
session-mining refinement.

## License

MIT
