---
name: loop-engine
description: >
  Odin-Loop engine. Runs, steps, inspects, lists, and authors workflow loops
  defined as YAML. Use whenever the user invokes /odin (run | step | status |
  list | new), or asks to run/continue/author a dev workflow loop, spec→harness
  →verify→implement→test cycle, or a custom loop.
---

# Odin-Loop Engine

You are the runtime for **Odin-Loop**: a system where a dev workflow *loop* is
**editable data** (a YAML file), and you execute it. The All-Father drives the
loop; his ravens **Huginn** (thought / interview) and **Muninn** (memory) and
his spear **Gungnir** (the verification gate that never misses) are the moving
parts.

This skill handles five actions, dispatched on the first argument of `/odin`:

| Command                | Action                                            |
| ---------------------- | ------------------------------------------------- |
| `/odin run`            | Start or continue the active run (hybrid drive)   |
| `/odin step <stage>`   | Re-run one specific stage, ignoring order         |
| `/odin status`         | Show the active run's state                        |
| `/odin list`           | List available loop definitions                   |
| `/odin new`            | Author a new custom loop by interview             |

> `/odin refine [loop]` (and `/odin refine apply`) is **not** handled here — it is
> the memory raven's job, handled by the **`muninn`** skill. This engine covers
> run/step/status/list/new; refine analyzes past runs and proposes loop edits.

If no run is active and the user types `/odin run`, ask which loop to start
(default to `spec-harness-tdd`).

---

## Where things live

| Thing                     | Path                                                  |
| ------------------------- | ----------------------------------------------------- |
| Built-in loop definitions | `<plugin>/loops/*.yaml`                                |
| User custom loops         | `<project>/.odin-loop/loops/*.yaml`                    |
| Active run state          | `<project>/.odin-loop/runs/<run-id>/state.json`        |
| Loop docs (spec, reports) | `<project>/.odin-loop/runs/<run-id>/`                  |
| Run harness & stubs       | `<project>/.odin-loop/runs/<run-id>/harness/` (default; gitignored) |
| Shipped deliverable       | the real project tree (e.g. `src/`, or tests meant to be committed) |

`<plugin>` is this plugin's root. Resolve loop names by checking the project
`.odin-loop/loops/` first, then the built-in `loops/`. Create `.odin-loop/`
directories as needed. Use the `date` command for any timestamps.

**Harness location.** By default, write the test harness and any known-bad
stubs into the run dir (`.odin-loop/runs/<run-id>/harness/`), NOT the repo root
— `.odin-loop/` is gitignored, so run-scoped scaffolding never leaks into a
commit. Make the harness location-independent (e.g. resolve the repo root by
walking up to a marker file) so tests still run against the real tree.
Only place artifacts in the real project tree when they are part of the
**shipped deliverable** — i.e. `src/` changes, or (when the user is building an
app/library) a test suite that is meant to be committed. In that case, say so
and "promote" the harness out of the run dir explicitly.

---

## state.json schema

```json
{
  "run_id": "20260614-143501-spec-harness-tdd",
  "loop": "spec-harness-tdd",
  "task": "<one-line description of what the user is building>",
  "started_at": "2026-06-14T14:35:01",
  "status": "running | awaiting_approval | done | failed",
  "current_stage": "interview",
  "iterations": { "implement": 2, "test": 2 },
  "total_iterations": 4,
  "max_iterations": 15,
  "artifacts": { "spec.md": ".odin-loop/runs/<id>/spec.md" },
  "interview": {
    "threshold": 0.15,
    "rounds": 4,
    "ambiguity": 0.13,
    "topology": ["Ingestion", "Normalization", "Review UI", "Export"]
  },
  "history": [
    { "stage": "interview", "result": "pass", "gate": "approved", "at": "..." },
    { "stage": "review", "result": "pass", "gate": "approved", "at": "...", "agent": "fresh" }
  ]
}
```

`iterations[stage]` counts how many times a gate failure looped back into that stage; `total_iterations` is their sum, checked against `max_iterations` on every loopback. Happy-path stage runs are not counted.

The optional `interview` object is written only by a deep-interview stage (`interview.mode: deep`): it mirrors the convergence the engine is tracking in `interview-log.md` so `/odin status` can show it. See `deep-interview.md` for the full procedure.

---

## `/odin run` — the hybrid drive

This is the core algorithm. Drive automatically, but **stop at human gates**.

1. **Load or create the run.**
   - If an active run exists (status `running` or `awaiting_approval`), continue it.
   - If status is `awaiting_approval` and the user is now invoking `/odin run`
     again, treat that as **approval** of the paused stage: record
     `gate: approved` in history, then advance to the next stage.
   - If no run exists, ask which loop (default `spec-harness-tdd`) and what the
     user is building, then **validate the resolved loop YAML** (see
     [Validating a loop](#validating-a-loop)) before creating the run — refuse to
     start a loop with blocking errors. Then create `state.json` and set
     `current_stage` to the first stage.

2. **Loop over stages** starting from `current_stage`:

   a. **Execute the stage.** Follow the stage's `goal` + `prompt`. Produce the
      declared `produces` artifacts.
      - **Execution context (`agent`).** `agent: fresh` is a recommendation, not a
        hard guarantee — this engine is itself an LLM, so the isolation is
        best-effort, not mechanically enforced. When a stage sets it, run that
        stage in a NEW sub-agent (Task/Agent) that has not seen this conversation:
        pass it only the stage `goal`/`prompt`, the task, the `consumes` artifacts
        (read fresh from disk), and the path(s) to write its `produces` to. The
        sub-agent writes its `produces` and assigns any blocking/non-blocking
        labels; prefer those labels at the gate rather than re-judging from the
        contaminated main thread. Don't quietly skip the sub-agent and judge
        inline — that defeats the point. If `agent` is absent or `inline`, run the
        stage yourself. (You may still use sub-agents for any heavy stage when
        helpful.)
      - For `interview`, actually interview the user — ask, wait, refine
        `spec.md` — do not invent answers (interview is always `inline`).
      - **Deep interview stages.** When the stage declares `interview.mode: deep`,
        don't just follow its `prompt` — run it per the **deep-interview playbook**
        (`deep-interview.md` in this skill dir). That means: confirm the work's
        **topology** (1–6 components) in Round 0, **self-score clarity** every round
        and record the convergence into `interview-log.md`, fire the **challenge
        schedule** (`interview.challenges`), and use the **auto-assist** sub-agents
        when `auto_assist` is on. The stage's gate reads `interview-log.md` (ambiguity
        ≤ `threshold`, every component covered). The `prompt` still supplies the
        domain framing; the playbook supplies the procedure.

   b. **Evaluate the gate.** Judge `gate.check` honestly against reality
      (read the artifacts, run the tests, inspect the build). Decide pass/fail.
      Never rationalize a pass — a false pass defeats the whole loop.

   c. **On gate FAIL:**
      - Increment `iterations[stage]` and `total_iterations`.
      - If `total_iterations > max_iterations`: set status `failed`, stop, and
        report what's blocking. Do not loop forever.
      - Jump to `gate.on_fail` if set, else retry the same stage. Continue.

   d. **On gate PASS:**
      - Append `{stage, result: pass, ...}` to history.
      - If `gate.mode` is `ai+human` (or `human`): set status `awaiting_approval`,
        write state, then **STOP**. Present a concise summary (what was produced,
        why the gate passed) and tell the user:
        > ✅ `<stage>` 게이트 통과. 검토 후 **승인하려면 `/odin run`**,
        > 수정이 필요하면 그냥 피드백을 말씀해 주세요.
      - If `gate.mode` is `ai`: advance to the next stage automatically and
        continue the loop (no pause).

   e. **End:** when the last stage's gate passes, set status `done` and report.

3. **Always persist `state.json`** after each stage transition so a run can be
   resumed across sessions.

When the user gives feedback instead of `/odin run` at a pause, treat it as a
revision request: re-run the current stage incorporating the feedback, then gate
again.

---

## `/odin step <stage-id>`

Run exactly one stage by id, regardless of `current_stage`, then evaluate its
gate and report — but do **not** auto-advance. Update `current_stage` to the
stepped stage. Use this for manual override / redo.

## `/odin status`

Read `state.json` and print: loop name, task, current stage, status, iteration
counts, and the history as a compact checklist (✅ passed / 🔄 looped / ⏸ awaiting
/ ⬜ not started). If an `interview` block is present, also show its convergence:
rounds so far, current ambiguity vs `threshold`, and the confirmed topology.

## `/odin list`

List loops from project `.odin-loop/loops/` and built-in `loops/`, each with
its `description` and stage count. Mark which is the active run's loop.

---

## `/odin new` — author a custom loop (dogfooding the philosophy)

Build the user's loop using the **same deep-interview principle** the default
loop preaches. Do not just dump a template — interview, then generate.

Ask (1–2 at a time):
1. What kind of work is this loop for? (general coding / a specific domain)
2. What are the stages, in order? For each: its **goal**.
3. For each stage, what is the **gate** — the testable condition to advance?
   And is that gate **ai** (auto) or **ai+human** (needs your approval)?
4. When a stage fails its gate, where should it **loop back** to (`on_fail`)?
5. What is the global `max_iterations` safety cap?
6. Does any stage need an *independent* review — a check that must not be biased
   by the work it inspects? If so, set `agent: fresh` on it so the engine runs it
   in a clean-room sub-agent. Default review/audit/QA stages to `agent: fresh`.
7. Does the loop open with a requirement-gathering interview? If so, offer the
   **deep interview** (`interview.mode: deep`): it confirms the work's components,
   tracks convergence to an ambiguity `threshold`, runs contrarian challenges, and
   can auto-assist. Capture `threshold` (default `0.15`), `challenges` (default
   `[contrarian@4, simplifier@6, ontologist@8]`), and `auto_assist` (default `true`).
   A deep interview stays `inline` and `produces` both `spec.md` and `interview-log.md`.

Then write a valid loop YAML (same schema as `loops/spec-harness-tdd.yaml`,
documented at its top) to `<project>/.odin-loop/loops/<name>.yaml`. **Validate the
written file** (see [Validating a loop](#validating-a-loop)) and fix anything it
flags. Then echo the file back, and offer to start it with `/odin run <name>`.

---

## Validating a loop

Loop structure is checked by code, not by remembering the rules. Run the bundled
validator on any loop YAML before a NEW run starts and after `/odin new` writes one:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_loop.py" <path/to/loop.yaml>
```

It emits a compact JSON report and signals via exit code: `0` valid (warnings may
remain), `1` blocking error(s) — **do not start the loop; report the `errors` and
fix them**, `2` usage error (unreadable file), `3` PyYAML not installed — validation
was skipped, so **fall back to the manual checks below**.

The rules it enforces (the same ones to apply by hand on exit 3): unique stage ids;
every `on_fail` points to a real stage id; every gate has a `mode`
(`ai`|`ai+human`|`human`) and a non-empty `check`; any `agent` is `inline` or
`fresh`; an `agent: fresh` stage declares a non-empty `consumes`. For any stage with
`interview.mode: deep`: it is not `agent: fresh`, its `produces` includes
`interview-log.md`, `threshold` (if set) is a number in (0, 1), and every
`challenges` entry matches `contrarian|simplifier|ontologist@<round>`.

---

## Principles (do not violate)

- **The loop is data.** Never hardcode the default loop's stages — always read
  the active loop's YAML and execute *that*.
- **Gates are honest.** A gate exists to stop bad work from advancing. If you
  cannot truthfully assert `gate.check`, the gate fails. No exceptions for
  convenience.
- **Hybrid means humans hold the wheel at `ai+human` gates.** Pause and wait.
- **Never weaken a harness to pass a gate.** Fix the implementation, not the test.
- **Fresh-agent stages are best-effort, not enforced.** `agent: fresh` asks for a
  sub-agent with no prior context; since the engine is an LLM, that isolation is a
  recommendation it should honor, not a guarantee. Don't quietly judge inline, and
  prefer the sub-agent's own labels at the gate.
- **Loopbacks are bounded** by `max_iterations`. Report, don't spin.
