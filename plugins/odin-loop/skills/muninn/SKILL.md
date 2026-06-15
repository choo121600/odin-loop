---
name: muninn
description: >
  Odin-Loop's memory raven. Analyzes your Odin-Loop run history and raw Claude
  Code session transcripts to find where you skip stages, re-work, or loop back,
  then proposes concrete edits to a loop's YAML. Use for `/odin refine`, or when
  the user asks to improve/tune/refine a loop based on past sessions or history.
---

# Muninn — the self-refining loop

Muninn ("memory") is the raven that flies over your past work and reports back.
This skill closes Odin-Loop's outer loop: **observe how you actually work →
propose edits to your loop definition → you approve → the loop improves.**

Triggered by `/odin refine [loop-name]`. If no loop name is given, default to the
active run's loop, else `spec-harness-tdd`.

## Pipeline

1. **Gather signals (cheap, deterministic).** Run the bundled analyzer — do NOT
   read raw transcripts into context (they can be megabytes):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/analyze_sessions.py" --cwd "$(pwd)"
   ```

   It emits compact JSON: Odin-Loop run history (loopbacks, gate failures,
   abandoned runs) plus raw-session heuristics (tool usage, `churn_ratio`,
   `avg_turns_before_first_edit`, `test_runs`, heavily-reworked files). It reports
   aggregates only — never message content.

2. **Read the target loop YAML** (`.odin-loop/loops/<name>.yaml` or the built-in
   `loops/<name>.yaml`) so proposals reference real stage ids and gates.

3. **Interpret signals → proposals.** Map signals to concrete, minimal edits.
   Prefer tightening an *earlier* gate over adding stages. Honest mapping:

   | Signal | Likely cause | Proposed edit |
   | --- | --- | --- |
   | `most_looped_stage` = implement (high loopbacks) | spec/plan/harness too weak; rework downstream | strengthen the `interview`, `plan`, or `harness-design` gate `check`; don't just raise `max_iterations` |
   | high `churn_ratio` (>2.5) + `test_runs` ≈ 0 | building without a verifiable target | recommend adopting/strengthening the harness stages; flag missing test discipline |
   | high `avg_turns_before_first_edit` | lots of deliberation before code | the `interview` and `plan` stages already capture this — confirm the `plan` gate is doing its job (the default loop has one), or add a `plan` stage if a custom loop lacks one |
   | runs `abandoned` at `interview` | interview too long / fatiguing | add a question cap hint to the interview `prompt`; split into must-have vs nice-to-have |
   | a gate always passes first try (no loopbacks, all `ai`) | gate may be rubber-stamping | suggest a stricter `check`, or flip to `ai+human` for that stage |
   | `gate_failures_by_stage` concentrated on one stage | that stage's `check` is hard to satisfy as written | clarify the `check` or split the stage |

   If `found_run_history` is false (no Odin-Loop runs yet), rely on raw-session
   heuristics only and SAY SO — they are softer signals.

4. **Write a proposal, do not auto-apply.** Save a refinement report to
   `.odin-loop/refinements/<timestamp>.md` (use `date` for the stamp) containing:
   - the signals that triggered each suggestion (cite the numbers),
   - a concrete unified-diff-style before/after of the loop YAML edits,
   - a one-line rationale per edit.
   Then present a summary and ask:
   > 🦅 무닌 제안 N건. 적용하려면 **`/odin refine apply`**, 개별 선택/수정은 말씀해 주세요.

5. **Apply only on approval.** When approved, edit the loop YAML in place
   (bump its `version`), and note in the report which edits were applied.

## Principles

- **Propose, never impose.** Same hybrid philosophy as the engine — the human
  approves every change. Muninn observes; it does not rewrite your loop silently.
- **Signals are heuristics, not verdicts.** State confidence. Don't invent a
  pattern the numbers don't support.
- **Privacy.** Work from the analyzer's aggregates. Do not dump transcript
  contents into context or into the report.
- **Minimal edits.** The smallest change that addresses the signal. Resist
  redesigning the whole loop from a single run.
