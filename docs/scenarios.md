# Odin-Loop — Scenarios

**English** | [한국어](scenarios.ko.md)

Three end-to-end walkthroughs. They show the *shape* of a session, not exact
output.

## Scenario 1 — A run with the default loop

You want to build something but the requirements are still fuzzy.

```
/odin run
  → no active run → engine asks which loop (default: spec-harness-tdd)
  → interview: a few focused questions; spec.md fills with testable criteria
  → ⏸ ai+human gate: review the spec, then /odin run to approve
/odin run
  → harness-design: each criterion becomes a test (red, no implementation yet)
  → harness-verify (Gungnir): a known-bad stub must fail ≥1 test (ai, auto)
  → implement: build against the harness · test: run it
  → a test fails → loops back to implement (bounded by max_iterations)
  → review (fresh agent, no prior context): checks src/ against spec.md
  → a blocking issue (spec/edge-case/security) → back to implement (fix adds a regression test); none → ⏸ ai+human sign-off → done
```

The interview is the point: most failures are intent failures, so the loop
refuses to write code until "done" has a testable definition.

## Scenario 2 — Authoring a custom loop (`/odin new`)

The default loop doesn't fit your work (say, a docs or research process).

```
/odin new
  → interview: what stages, in order? each stage's goal?
  → for each stage: the gate check, and ai or ai+human?
  → where does each stage loop back on failure (on_fail)?
  → max_iterations cap?
  → any stage that needs an independent review? → mark it agent: fresh
  → writes .odin-loop/loops/<name>.yaml (validated) and offers /odin run <name>
```

Because a loop is just data, your custom loop runs through the exact same engine
and gates as the built-in one.

## Scenario 3 — Refining a loop (`/odin refine`)

After a few runs, you notice you keep reworking the same stage.

```
/odin refine
  → analyzer reads run history + session aggregates (never message content)
  → e.g. "implement loops back a lot" → proposal: tighten the interview gate
  → writes a refinement report with before/after YAML diffs — nothing applied yet
/odin refine apply
  → applies the approved edits and bumps the loop's version
```

Muninn closes the outer loop: the process learns from how you actually work,
and you approve every change.

---

See also: [Design](design.md) · [Features](features.md) · [← README](../README.md)
