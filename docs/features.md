# Odin-Loop — Features

**English** | [한국어](features.ko.md)

What Odin-Loop can do, command by command.

## Command surface

Everything is driven through `/odin <subcommand>`:

| Command | What it does |
| --- | --- |
| `/odin run` | Start or continue the active run. Auto-advances `ai` gates, pauses at `ai+human` gates. |
| `/odin step <stage>` | Re-run exactly one stage by id, without auto-advancing. Manual override / redo. |
| `/odin status` | Print the active run's loop, task, current stage, and history checklist. |
| `/odin list` | List available loop definitions (project + built-in) with their stage counts. |
| `/odin new` | Author a new custom loop by interview, then write it to `.odin-loop/loops/`. |
| `/odin refine [loop]` | Mine past runs & sessions and propose loop edits (Muninn). |
| `/odin refine apply` | Apply the most recent refinement proposal. |

`run`/`step`/`status`/`list`/`new` are handled by the engine; `refine` is handled
by the Muninn skill.

## Hybrid execution

`/odin run` drives the loop on its own but **stops at every `ai+human` gate**, so
you keep control at the decisions that matter. To approve a paused stage, run
`/odin run` again. To revise it instead, just type feedback — the stage re-runs
with your changes and re-gates. Loopbacks are bounded by `max_iterations`.

## The default loop: `spec-harness-tdd`

The shipped loop encodes a spec-driven, test-first discipline:

```
interview → harness-design → harness-verify → implement → test
 (Huginn)                      (Gungnir)            ↑__________|
```

1. **interview** — turn a vague request into testable acceptance criteria (`ai+human`).
2. **harness-design** — translate each criterion into an executable test (`ai`).
3. **harness-verify** — prove the harness has teeth: a deliberately-wrong stub must
   make at least one test fail (`ai+human`).
4. **implement** — build against the verified harness, without weakening tests (`ai`).
5. **test** — run the harness; loop back to `implement` on failure (`ai`).

## Authoring your own loop

`/odin new` interviews you for stages, gates (`ai` vs `ai+human`), and `on_fail`
loopbacks, then writes a valid loop YAML. The engine validates unique stage ids,
that every `on_fail` points to a real stage, and that every gate has a mode and a
check before saving.

## Muninn — self-refinement

`/odin refine` runs a bundled analyzer over your run history and raw session
transcripts (aggregates only — never message content), then proposes concrete,
minimal edits to a loop's YAML — for example, tightening an earlier gate when a
later stage loops back a lot. Nothing is applied until you run `/odin refine apply`.

---

See also: [Design](design.md) · [Scenarios](scenarios.md) · [← README](../README.md)
