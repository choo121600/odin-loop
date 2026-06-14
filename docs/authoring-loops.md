# Authoring Custom Loops

Odin-Loop ships with a built-in loop (`spec-harness-tdd`), but its real power is
that **a loop is just data** — a YAML file you can write yourself. This guide
takes you from "I've never thought about loops" to a custom loop you can start
with `/odin run`.

You don't write any code. You describe a workflow as a list of stages, each with
a goal and a gate, and the engine runs it for you. By the end of this guide
you'll have a working loop of your own that you can start with one command.

> **Prerequisites:** Claude Code with the `odin-loop` plugin installed (so
> `/odin list` works), a project directory, and basic YAML familiarity.
> Installing the plugin and the day-to-day `run`/`step`/`status` mechanics are
> out of scope here — see `docs/features.md` for those.

---

## 1. What is a loop, and when would you author one?

A **loop** is a repeatable workflow written as data. The engine reads your YAML
and walks through its **stages** in order, only moving forward when a stage's
**gate** says the work is good enough. If a stage fails its gate, the engine
loops back to an earlier stage and tries again — hence "loop."

You are not programming the engine; you are describing a process, and the engine
*enforces* it — it won't let work advance past a gate that doesn't pass.

Author your own loop when the built-in `spec-harness-tdd` doesn't match the work
you actually do — for example a writing process, a review checklist, a release
routine, or a research procedure. If your work has clear stages and you can
state an objective "is this good enough?" check between them, it's a good fit.

---

## 2. Core concepts (the vocabulary)

You'll meet these terms in every loop file. Here is the whole vocabulary, in
plain language:

- **loop** — the whole workflow: a `name`, a `description`, a global
  `max_iterations` cap, and an ordered list of `stages`.
- **stage** — one step of work. It has an `id`, a `title`, a `goal` (what it must
  achieve), a `prompt` (instructions the engine follows to do the stage), and a
  `gate`.
- **goal** — the intent of the stage, in one sentence. "What must be true when
  this stage is done."
- **gate** — the advance condition. The engine will not move past a stage until
  its gate passes. A gate has a `mode` and a `check` (and optionally `on_fail`).
- **gate mode** — *who* decides, and whether the loop pauses:
  - `ai` — the engine judges the check and **auto-advances** on pass (no pause).
  - `ai+human` — the engine judges the check, then **pauses for your approval**
    before advancing.
  - `human` — you decide directly.
- **gate check** — the testable assertion the gate evaluates, e.g. "all tests in
  `harness/` pass." Write it so it's observable, not a matter of opinion.
- **on_fail** — the stage `id` to jump back to when the gate fails. Omit it to
  simply retry the same stage.
- **max_iterations** — a global safety cap on the total number of stage runs. It
  stops a loop from spinning forever; when total runs exceed it, the engine
  stops and reports instead of looping again.

---

## 3. The loop file: where it lives & its schema

A custom loop is one YAML file. Put it at:

```
<project>/.odin-loop/loops/<name>.yaml
```

The `<name>` should match the loop's `name:` field. When you run a loop by name,
the engine resolves it by checking your **project** `.odin-loop/loops/` first,
then the **built-in** loops — so a project loop can shadow a built-in one.

The schema, top to bottom:

```yaml
name: my-loop            # unique loop id (matches the filename)
version: 1               # integer; bump on breaking edits
description: one-liner   # shown in `/odin list`
max_iterations: 12       # global safety cap on total stage runs

stages:
  - id: first-stage      # unique stage id
    title: First Stage   # human-readable label
    goal: what this stage must achieve
    prompt: |            # instructions the engine follows to run the stage
      Do the thing. Be specific about what "done" looks like.
    consumes: [some-input.md]   # artifacts this stage reads   (hints, optional)
    produces: [some-output.md]  # artifacts this stage writes  (hints, optional)
    gate:
      mode: ai           # ai | ai+human | human
      check: the observable condition that must be true to advance
      on_fail: first-stage   # stage id to jump to on failure (optional)
```

`consumes` and `produces` are hints that document the data flow between stages;
they help the engine (and you) see which artifacts each stage reads and writes.

---

## 4. Designing stages, gates & loopbacks

Three decisions make or break a loop.

**Split work into stages.** Each stage should have one clear goal and produce one
kind of artifact. A good seam between two stages is a point where you'd naturally
want to *check the work before continuing*. If you can't name a check between two
steps, they're probably one stage.

**Choose the gate mode.** Use `ai+human` at the moments where your judgment
matters most and a wrong turn is expensive to undo — typically framing decisions
and final sign-off. Use `ai` for mechanical checks the engine can judge on its
own (build passes, every section written) so the loop doesn't stop to ask about
things you don't need to see.

**Write a *testable* check.** The check must be observable, not a matter of
taste. Compare:

- Bad: `check: the document reads well` — no one can objectively pass/fail this.
- Good: `check: every section listed in the outline has prose with no TODOs` —
  anyone can look and know.

**Design the loopback.** When a gate fails, `on_fail` decides where to go. Point
it at the *earliest stage that can fix the problem*. A test stage that fails
should usually loop back to the implementation stage, not all the way to the
spec. Omit `on_fail` to just retry the same stage. Finally, set
`max_iterations` high enough to allow a few honest retries but low enough that a
stuck loop stops and reports instead of spinning — `12` is a sensible default.

---

## 5. Two ways to author your loop

### (a) By hand

1. Create `<project>/.odin-loop/loops/<name>.yaml`.
2. Fill in `name`, `version`, `description`, and `max_iterations`.
3. Add your `stages`, each with an `id`, `title`, `goal`, `prompt`, and `gate`.
4. Save, then validate and run it (see §7).

Copying the built-in `spec-harness-tdd.yaml` and editing it is a fine starting
point — its header documents every field.

### (b) Via `/odin new` (guided interview)

If you'd rather be interviewed than start from a blank file, run:

```
/odin new
```

The engine asks you, a couple of questions at a time:

1. What kind of work is this loop for?
2. What are the stages, in order, and each one's goal?
3. For each stage, what's the gate check — and is it `ai` or `ai+human`?
4. When a stage fails its gate, where should it loop back to (`on_fail`)?
5. What's the global `max_iterations` cap?

It then writes a valid loop YAML to `.odin-loop/loops/<name>.yaml`, echoes it
back, and offers to start it with `/odin run <name>`.

---

## 6. Worked example: the `tech-docs` loop

Here is a complete custom loop for writing technical docs. It frames the doc,
outlines it, drafts it, fact-checks every claim, then revises. The YAML below is
abbreviated for space: every `id`, `title`, `goal`, gate `mode`, and `on_fail`
is shown verbatim, while the long `prompt` bodies and `check` texts are trimmed
(shown with `...`). The full file lives at `.odin-loop/loops/tech-docs.yaml`.

```yaml
name: tech-docs
version: 1
description: Frame audience/goal -> outline -> draft -> fact-check -> revise (technical docs / README)
max_iterations: 12

stages:
  - id: brief
    title: Frame the Doc (Huginn)
    goal: Pin down audience, purpose, scope, and testable success criteria before any writing
    prompt: |
      Interview the user before writing a single line of prose ...
    produces: [brief.md]
    gate:
      mode: ai+human
      check: brief.md names a specific audience and a single clear purpose, ...

  - id: outline
    title: Outline & Structure
    goal: Lock the section structure and logical flow that will satisfy every success criterion
    prompt: |
      Design the skeleton before writing prose ...
    consumes: [brief.md]
    produces: [outline.md]
    gate:
      mode: ai+human
      check: outline.md maps every success criterion to a section and vice versa ...

  - id: draft
    title: Draft the Prose
    goal: Write complete prose for every outlined section, with no placeholders
    prompt: |
      Write the actual document into doc.md, following outline.md ...
    consumes: [brief.md, outline.md]
    produces: [doc.md]
    gate:
      mode: ai
      check: Every section in outline.md has complete prose in doc.md, no placeholders ...

  - id: fact-check
    title: Fact-Check (Gungnir - the spear that never misses)
    goal: Verify every claim, number, command, path, and code sample against reality
    prompt: |
      Treat every checkable assertion in doc.md as guilty until verified ...
    consumes: [doc.md]
    produces: [fact-check-report.md]
    gate:
      mode: ai
      check: every checkable assertion verified, zero FAIL or unverifiable items remain
      on_fail: draft

  - id: revise
    title: Revise & Sign-Off
    goal: A genuine critique and edit pass for clarity, redundancy, and audience fit
    prompt: |
      Do a real editing pass -- not a "looks good" ...
    consumes: [brief.md, outline.md, doc.md, fact-check-report.md]
    gate:
      mode: ai+human
      check: a critique pass applied with concrete edits, doc satisfies every success criterion
```

Why it's shaped this way:

- **`brief` and `outline` are `ai+human`.** Audience/goal framing and structure
  are where a wrong turn is most expensive, so the loop pauses for your approval
  before any prose is written.
- **`draft` and `fact-check` are `ai`.** These are mechanical: "is every section
  written?" and "is every claim verified?" The engine can judge both and
  auto-advance, so it doesn't interrupt you.
- **`fact-check` has `on_fail: draft`.** If a claim doesn't check out, the fix is
  in the prose, so the loop jumps back to `draft` — not all the way to `brief`.
- **`revise` is `ai+human`.** The last stage is your final sign-off on the
  finished document.

---

## 7. Validate, run, and where to go next

Before running, check your YAML against the rules the engine validates:

- Every **stage `id` is unique**.
- Every **`on_fail` points to a real stage `id`** in the same loop.
- Every **gate has both a `mode` and a `check`**.

Then confirm the engine can see it and start it:

```
/odin list              # your loop appears, with its description and stage count
/odin run <name>        # starts the loop at its first stage
/odin status            # shows the active run's state at any time
```

On `/odin run <name>`, the engine creates a run, sets the first stage as current,
executes it, and evaluates its gate. If that first gate is `ai+human`, the loop
pauses and waits for your `/odin run` approval; if it's `ai`, it auto-advances.

**Where to go next (out of scope for this guide):**

- To improve a loop based on past runs, see `/odin refine` and the **muninn**
  skill — that's a separate workflow from authoring.
- For the full mechanics of `run`, `step`, and `status`, see `docs/features.md`
  and `docs/design.md`.
