# Odin-Loop

**English** | [한국어](README.ko.md)

[![version](https://img.shields.io/github/v/release/choo121600/odin-loop?label=version&color=brightgreen)](CHANGELOG.md)
![status: actively developed](https://img.shields.io/badge/status-actively%20developed-brightgreen.svg)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> Author, run, and refine your own AI dev workflow *loops* — as editable data.

Most "AI dev workflow" tools hand you **one fixed loop**. Odin-Loop treats the
loop itself as a first-class, editable artifact: a YAML file the engine reads and
executes. It ships with a strong default loop, and lets you build and refine your
own with `/odin new`.

```
deep interview → plan → harness design → harness verify → implement → test → clean review
   (Huginn)     (planner) (executor)    (critic·Gungnir) (executor) (executor)  (reviewer)
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
  coding failures. The interview confirms the work's **components** (topology),
  probes a fixed set of dimensions, and **self-scores clarity each round** until
  ambiguity drops below a threshold — injecting contrarian challenges and auto-assist
  along the way. It turns a vague request into *testable acceptance criteria* —
  captured in a structured `spec.md`, with the convergence trail in `interview-log.md`
  — before any code is written. (See [Design → Deep interview](docs/design.md#deep-interview-huginn).)
- **Harness before implementation** — the criteria become executable tests, so
  "done" has an objective definition.
- **Verify the harness itself (Gungnir)** — the step most tools skip. A test that
  always passes proves nothing. We run a deliberately-wrong stub and require at
  least one test to *fail* — proving the harness has teeth.
- **Then implement and test** — implement against the verified harness; loop back
  on failure, bounded by a `max_iterations` cap.
- **Review with a clean agent** — a final `reviewer`-role stage (clean-room, no
  prior context) reviews the result with no memory of how it was built, catching
  what the harness can't encode
  (missed edge cases, scope creep); an objectively-defined *blocking* finding loops
  back to `implement` (the fix adds a regression test), and the stage pauses for
  your sign-off.

## Install

```
/plugin marketplace add choo121600/odin-loop
/plugin install odin-loop@odin-loop
```

## Quickstart

On your first `/odin run`, Odin-Loop asks which loop to use (default
`spec-harness-tdd`) and begins a deep interview — turning your request into
testable acceptance criteria before any code is written.

```
/odin run        # no active run → pick a loop, then interview
/odin status     # see where the run is
```

It pauses at every `ai+human` gate; approve by running `/odin run` again, or type
feedback to revise that stage.

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

## Documentation

- [Design](docs/design.md) — architecture, the loop-as-data model, gates & state
- [Features](docs/features.md) — every command, the default loop, Muninn
- [Scenarios](docs/scenarios.md) — end-to-end walkthroughs
- [Authoring custom loops](docs/authoring-loops.md) — write your own loop as YAML

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

Built-in loops live in `plugins/odin-loop/loops/`; your custom loops live in
`.odin-loop/loops/` in your project. Run state lives in `.odin-loop/runs/`.

### Stage roles

Each stage can name **who** runs it via `agent`: `inline` (the engine itself),
`fresh` (a generic clean-room sub-agent), or one of five reusable roles shipped in
[`plugins/odin-loop/agents/`](plugins/odin-loop/agents/):

| `explore` | `planner` | `executor` | `critic` | `reviewer` |
| --- | --- | --- | --- | --- |
| read-only scout | spec → plan | implement & test | adversarial verify (Gungnir) | clean review |

`explore` / `critic` / `reviewer` run **fresh** (clean-room) by default; `planner` /
`executor` run **inline**. Override per stage with `agent: { role: reviewer, fresh: false }`.
The role shapes *how* a worker behaves; the stage's gate and artifacts stay in the YAML.

## Status

`v0.6.0` — actively developed; the default loop runs end-to-end. See
[CHANGELOG.md](CHANGELOG.md) for the full version history.

## License

MIT
