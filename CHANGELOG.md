# Changelog

All notable changes to Odin-Loop are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
  Muninn (`/odin refine`) session-mining refinement.

[0.6.0]: https://github.com/choo121600/odin-loop/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/choo121600/odin-loop/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/choo121600/odin-loop/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/choo121600/odin-loop/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/choo121600/odin-loop/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/choo121600/odin-loop/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/choo121600/odin-loop/releases/tag/v0.1.0
