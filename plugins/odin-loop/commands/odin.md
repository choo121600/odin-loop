---
description: Run, step, inspect, list, author, or refine Odin-Loop workflow loops
argument-hint: "run | step <stage> | status | list | new | refine [loop]"
allowed-tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "Task", "Skill"]
---

The user invoked the **Odin-Loop** engine.

Arguments: `$ARGUMENTS`

Dispatch on the first argument:

- `run` — start or continue the active run (hybrid: auto-advance, pause at
  `ai+human` gates for approval). → use the **`loop-engine`** skill.
- `step <stage-id>` — re-run one specific stage without auto-advancing. → **`loop-engine`**.
- `status` — show the active run's state. → **`loop-engine`**.
- `list` — list available loop definitions. → **`loop-engine`**.
- `new` — author a new custom loop by interviewing the user. → **`loop-engine`**.
- `refine [loop]` — analyze past runs + sessions and propose loop edits. → use
  the **`muninn`** skill.
- `refine apply` — apply the most recent refinement proposal. → **`muninn`**.

If no argument is given, default to `status` if a run exists, otherwise explain
the available subcommands briefly and offer to start one.

Follow the engine's rules exactly: gates must be judged honestly, `ai+human`
gates must pause for the user, and loopbacks are bounded by `max_iterations`.
