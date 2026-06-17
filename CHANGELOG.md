# Changelog

All notable changes to Odin-Loop are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_Add new entries here as you merge changes, grouped under `Added` / `Changed` /
`Fixed` / `Removed`. On release, rename this heading to the new version
(e.g. `## [0.7.0] — YYYY-MM-DD`), tag it, and start a fresh `Unreleased` section._

## [0.7.3] — 2026-06-17

### Fixed
- **A scheduled run that fails is now reported as a failure.** The fire-time
  runner recorded any run whose `claude -p` returned as `status: "ran"` regardless
  of its exit code, so a non-zero exit (e.g. hitting a Claude usage limit mid-run)
  was logged as a success — it did not count toward `recent_failures`, and a
  `notify: on-failure` policy stayed silent, so `schedule list` health looked
  falsely green. A non-zero exit is now a distinct **`failed`** outcome (vs
  `error` = claude could not be launched at all): it is counted in
  `recent_failures`, surfaced by `on-failure` / `always` notifications (with the
  exit code in the body), and returns a non-zero CLI exit. Surfaced by a real
  18:00 scheduled fire that hit a usage limit and was mis-reported as `ran`.

## [0.7.2] — 2026-06-17

### Fixed
- **Scheduled runs actually run the loop now.** The fire-time runner invoked
  `claude -p "/odin run <loop>"`, but a marketplace-plugin command is only valid when
  **qualified** — bare `/odin` prints `Unknown command: /odin` and silently no-ops. The
  runner now spawns `/odin-loop:odin run <loop>`, verified by a real launchd fire
  (the loop ran end-to-end). Surfaced by integration testing the scheduler.

### Changed
- **Docs and skills use the qualified `/odin-loop:odin …` form.** Every `/odin run`,
  `/odin schedule`, etc. in the README, `docs/`, and skill files was a bare `/odin`,
  which Claude Code does not resolve for a marketplace plugin — all replaced with the
  working `/odin-loop:odin` form.

## [0.7.1] — 2026-06-17

### Fixed
- **Scheduled runs now find `claude`.** The launchd plist / crontab trigger ran with a
  PATH that omitted `~/.local/bin` (a common `claude` install location), so a real
  scheduled fire failed `claude not found`. The runner now resolves claude's absolute
  path, and the trigger PATH includes the user bin dirs (`~/.local/bin`, `~/bin`).

## [0.7.0] — 2026-06-17

The **scheduler** release (Hermóðr): run a fully-autonomous loop unattended on the OS
scheduler (launchd / crontab), with outcome notifications and at-a-glance runtime status
in `list`.

### Added
- **Scheduling (Hermóðr).** Register a fully-autonomous loop (every gate `ai`, no
  human gate) to run unattended on the OS scheduler (macOS launchd / crontab) via
  `/odin-loop:odin schedule register|install|list|remove|uninstall`. Schedulability is enforced
  at register **and** on every fire (`validate_loop.py --schedulable`); the unattended
  run is contained by a conservative scoped settings profile (never
  `--dangerously-skip-permissions`), an explicit outward-action acknowledgment, an
  overlap lock, and a run log. Docs: [`docs/scheduling.md`](docs/scheduling.md) (#30).
- **Scheduled-run notifications.** A scheduled loop emits a best-effort desktop
  notification on its outcome, controlled by a per-schedule
  `notify: off | on-failure | always` policy (default `on-failure`) —
  `/odin-loop:odin schedule register … --notify`. OS-native (macOS `osascript` / Linux
  `notify-send`, no extra dependency); a notify failure is logged and never changes the
  run's outcome or exit status.
- **Schedule status in `list`.** `/odin-loop:odin schedule list` now shows each schedule's runtime
  health — last fire time + outcome (or `never`), a recent-failure count, and the next
  fire time computed from the cron — alongside its install status. Read-only; log parsing
  and the next-fire computation are best-effort.

## [0.6.1] — 2026-06-16

A documentation-and-consistency patch: no behavior changes to how you author or
run loops, plus muninn / validator fixes that landed since 0.6.0.

### Added
- `CHANGELOG.md` following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
  + Semantic Versioning, extracted from the README Status section (#26).

### Fixed
- **muninn** counts stage loopbacks directly instead of `iterations − 1` (#5).
- **muninn** uses a canonical history-gate vocabulary and no longer double-counts
  `ai+human` gates (#13).
- **validate_loop** requires a deep-interview stage's `produces` to be a list (#12).
- `marketplace.json`'s pipeline description now matches the real stage names in
  `plugin.json` and the loop YAML — `harness-design → harness-verify` (#10).
- `spec-harness-tdd.yaml` references the deep-interview playbook by its full
  `skills/loop-engine/deep-interview.md` path instead of a bare filename (#14).
- `state.json` `interview`-object field contract reconciled across `SKILL.md` and
  `deep-interview.md`: the written set is `{ threshold, rounds, ambiguity,
  topology }` (what `/odin-loop:odin status` reads); per-component clarity stays in
  `interview-log.md` (#15).
- Korean authoring-loops guide is reachable and self-consistent — added the EN/KO
  language switcher, pointed its cross-references at the `.ko.md` siblings, and
  linked the guide from both Documentation indexes (#7, #8, #9).

## [0.6.0] — 2026-06-15

### Added
- **Named stage roles.** A stage's `agent` can now be one of five reusable
  personas — `explore` / `planner` / `executor` / `critic` / `reviewer` — shipped
  in `plugins/odin-loop/agents/`. Each has a default clean-room/inline context
  (`explore` / `critic` / `reviewer` run **fresh**; `planner` / `executor` run
  **inline**) that you can override per stage via `agent: { role, fresh }`. The
  default loop runs its stages as these roles.

## [0.5.0] — 2026-06-15

### Added
- Implementation **plan** stage between the interview and the harness.

## [0.4.0] — 2026-06-15

### Added
- **Deep-interview playbook**: multi-component topology, per-round clarity
  self-scoring that converges to an ambiguity threshold, and
  contrarian/simplifier/ontologist challenges with auto-assist.
- Deterministic loop validator (`scripts/validate_loop.py`).

## [0.3.0] — 2026-06-15

### Added
- Clean-room **review** stage.
- `agent: inline | fresh` selector for stage execution context.

## [0.2.0] — 2026-06-14

### Changed
- Deeper interview: 8-dimension gate and a structured `spec.md` output.

## [0.1.1] — 2026-06-14

### Fixed
- Engine now defaults the harness into the run directory.

## [0.1.0] — 2026-06-14

### Added
- Initial release: the loop engine, the default loop, custom-loop authoring, and
  Muninn (`/odin-loop:odin refine`) session-mining refinement.

[Unreleased]: https://github.com/choo121600/odin-loop/compare/v0.7.3...HEAD
[0.7.3]: https://github.com/choo121600/odin-loop/compare/v0.7.2...v0.7.3
[0.7.2]: https://github.com/choo121600/odin-loop/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/choo121600/odin-loop/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/choo121600/odin-loop/compare/v0.6.1...v0.7.0
[0.6.1]: https://github.com/choo121600/odin-loop/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/choo121600/odin-loop/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/choo121600/odin-loop/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/choo121600/odin-loop/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/choo121600/odin-loop/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/choo121600/odin-loop/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/choo121600/odin-loop/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/choo121600/odin-loop/releases/tag/v0.1.0
