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
interview → plan → harness-design → harness-verify → implement → test → review
 (Huginn)                             (Gungnir)            ↑__________|______|
                                                                (fresh agent)
```

1. **interview** — turn a vague request into a structured `spec.md`. It runs the
   **deep-interview playbook** (`interview.mode: deep`): confirm the work's
   **topology** (1–6 components), probe eight dimensions, and **self-score clarity
   each round** into `interview-log.md` until ambiguity drops to the `threshold`.
   Scheduled **contrarian / simplifier / ontologist** challenges attack the emerging
   spec, and read-only **auto-assist** sub-agents propose candidate answers or resolve
   opt-outs (never deciding for you). The gate reads the convergence ledger — every
   component covered by a testable criterion, ambiguity ≤ threshold (`ai+human`).
   See [Design → Deep interview](design.md#deep-interview-huginn).
2. **plan** — turn the spec (the *what*) into an ordered implementation plan (the
   *how*): decompose the confirmed topology into build units, name the file/module
   targets, map each unit to the criteria it closes, and sequence them with no unmet
   dependency. Runs `inline` — planning wants the interview's context, not fresh eyes.
   The gate checks that every criterion maps to a build unit and the order is
   actionable, then pauses for your sign-off (`ai+human`).
3. **harness-design** — translate each criterion into an executable test (`ai`).
4. **harness-verify** — prove the harness has teeth: a deliberately-wrong stub must
   make at least one test fail (`ai`).
5. **implement** — build against the verified harness, following the plan's build
   order, without weakening tests (`ai`).
6. **test** — run the harness; loop back to `implement` on failure (`ai`).
7. **review** — a *fresh* sub-agent (no prior context, `agent: fresh`) reviews the
   implementation against `spec.md` for what the harness can't catch (missed edge
   cases, scope creep). "Blocking" is defined objectively (a spec criterion/edge-case
   violation, or a security/data-loss defect); a blocking finding loops back to
   `implement` (the fix adds a regression test), and the stage pauses for your
   sign-off (`ai+human`).

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
