# Scheduling Autonomous Loops (Hermóðr)

**English** | [한국어](scheduling.ko.md)

> Hermóðr is Óðinn's herald — the part of Odin-Loop that runs his errands on a
> schedule. It registers a **fully-autonomous** loop (one with no human gate) with the
> OS scheduler so it fires **unattended**, and it is the runner that drives each tick.

## Overview

`/odin run` keeps you in the loop: it pauses at every `ai+human` gate for your
approval. Some loops, though, have **no human gate at all** — every gate is `ai`, so
they run start to finish on their own (the daily board loops, a PR-merge loop, an
audit-to-issues loop). Those are the loops Hermóðr can put on a schedule.

The model is one line:

> Hermóðr schedules **only loops that never pause for a human**, so an unattended run
> can never silently auto-approve a checkpoint. *Humans hold the wheel at `ai+human`
> gates* is preserved **by construction** — a human-gated loop is simply refused.

Scheduling is two explicit steps: **`register`** writes the schedule as data, and
**`install`** wires it into the OS scheduler (macOS launchd or a crontab entry). That
split lets you review a schedule before anything touches your system.

## Prerequisites

- **Odin-Loop installed** and working (`/odin run` drives a loop for you).
- **A fully-autonomous loop** to schedule — every gate `ai`, no `interview` stage. See
  [Which loops can be scheduled](#which-loops-can-be-scheduled).
- The **`claude` CLI logged in** — the scheduled run is a headless `claude -p` process
  and uses your existing credentials.
- **macOS** (uses launchd) or **Linux** (uses crontab).

## Which loops can be scheduled

A loop is **schedulable** only if it never stops for a human: **every gate is `ai`**
(no `ai+human`, no `human`) and **no stage runs an `interview`**. Anything else is
refused — registering it would either block forever waiting for an approval that never
comes, or silently auto-approve a checkpoint that exists for a reason.

`register` runs this check for you and refuses a loop that fails it. To check a loop
ahead of time, run the validator directly (`$CLAUDE_PLUGIN_ROOT` is the installed
plugin's root):

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/validate_loop.py" --schedulable <path/to/loop.yaml>
# exit 0 → schedulable · exit 1 → not (it prints which stage blocks it)
```

The line falls exactly where you'd want it. Of the loops that ship with Odin-Loop,
`audit-to-issues`, `daily-issue-plan`, and `pr-review-merge` are schedulable; the ones
that gather intent or take a sign-off — `daily-issue-run` (its `triage` gate),
`tech-docs` (its `brief` gate), and `spec-harness-tdd` (interview / plan / review) —
are not.

### Want to schedule a human-gated loop anyway?

Author an **autonomous variant**. "Loops are data," so make a copy whose human gate is
lowered to `ai` (the AI decides instead of pausing) and schedule that one. Removing a
human gate is not free — that checkpoint was a safety net — so tighten the automated
gates around the hole (default to the more conservative branch, keep the clean-review
gate strict). Do it as a deliberate authoring act with `/odin new` or a hand copy; the
scheduler will not do it for you.

## Quickstart

Schedule `daily-issue-plan` to fill your board every morning at 09:00.

**1. Register** the schedule (validates it, then writes it as data):

```
/odin schedule register daily-issue-plan "0 9 * * *"
```

`register` checks schedulability, then surfaces the loop's **outward-facing actions**
(things like `git push`, `gh pr create`) and asks you to acknowledge that they will run
unattended. On your **explicit yes**, it writes:

- `.odin-loop/schedules/daily-issue-plan.yaml` — the schedule, as data
- `.odin-loop/schedules/daily-issue-plan.settings.json` — a conservative permission
  profile for the unattended run (see [The safety model](#the-safety-model))

Nothing has touched your OS yet.

**2. Install** the OS trigger:

```
/odin schedule install daily-issue-plan
```

On macOS this writes a LaunchAgent at
`~/Library/LaunchAgents/com.odin-loop.hermod.daily-issue-plan.plist` and loads it; on
Linux it adds a crontab line. The trigger runs
`claude -p "/odin run daily-issue-plan" --settings <profile>` at 09:00 each day.

**3. Verify** it fired — read the run log:

```bash
cat .odin-loop/schedules/daily-issue-plan.log
```

Each tick appends a line: that it started, the schedulability re-check, and the exit
status (or a refusal / skip). If the log shows a run at 09:00, the schedule works.

## The safety model

"No human gate" is **necessary but not sufficient** for a safe unattended run — an
all-`ai` loop can still take destructive outward actions (a PR-merge loop *merges*; a
build loop *ships*). Hermóðr closes that gap with three layers:

- **Blast-radius acknowledgment.** At `register`, the loop's outward-facing actions
  (`git push`, `gh pr create`, `gh pr merge`, `gh issue create`, board moves) are
  detected from its stage prompts and listed, and you must explicitly acknowledge them
  before the schedule is written. `list` keeps that acknowledged set visible.
- **A scoped settings profile.** The unattended run is launched with
  `--settings .odin-loop/schedules/<loop>.settings.json` — **never**
  `--dangerously-skip-permissions`. The default profile is deliberately narrow:
  `Read`/`Write`/`Edit`/`Glob`/`Grep` plus only the scoped `Bash(<tool>:*)` entries the
  loop actually needs (e.g. `Bash(git:*)`, `Bash(gh:*)`), with `rm`/`sudo` denied. It is
  a plain JSON file you can edit — **widen** it if the run needs a tool it lacks,
  **narrow** it to lock the run down further.
- **Fire-time re-validation.** Schedulability is re-checked on **every** fire, not just
  at registration. If the loop has since gained a human gate or an interview stage, the
  run **refuses and logs** instead of executing — it never drives the loop into a pause.

## Managing schedules

List every schedule with its cron, install status, acknowledged outward actions, and its
**runtime health** — the last fire's time + outcome (or `never`), a recent-failure count,
and the next scheduled fire time (computed from the cron):

```
/odin schedule list
```

Remove one — this **uninstalls the OS trigger if it is installed**, then deletes the
declaration and its profile, so nothing is left firing against a schedule you removed:

```
/odin schedule remove daily-issue-plan
```

`uninstall` unloads the trigger but keeps the declaration, if you want to stop a
schedule without forgetting it:

```
/odin schedule uninstall daily-issue-plan
```

## Notifications

A scheduled run only writes its outcome to the log; turn on a desktop **notification**
so a failure is noticed without reading it. Set the policy at `register`:

```
/odin schedule register daily-issue-plan "0 9 * * *" --notify on-failure
```

- `on-failure` (default) — notify only on a real problem (an `error`, or a `refused`
  fire-time re-check); stays quiet on success and on a benign lock skip.
- `always` — notify on every run, including success.
- `off` — never notify.

The notification is **best-effort**: it uses an OS-native mechanism (macOS `osascript`,
Linux `notify-send` — no extra install) and may not display if there is no active GUI
session, so the **run log remains the source of truth**. A notification failure is
logged and never changes the run's outcome.

## launchd vs crontab

`install` picks the backend from your OS, or you can force it. On **macOS** it writes a
LaunchAgent plist to `~/Library/LaunchAgents/com.odin-loop.hermod.<loop>.plist` (it
survives logout/reboot); on **Linux** it adds a `crontab` line. Override the choice when
registering with `--platform launchd|cron|auto`.

Inspect the installed trigger directly:

```bash
# macOS
cat ~/Library/LaunchAgents/com.odin-loop.hermod.daily-issue-plan.plist
# Linux
crontab -l | grep hermod
```

launchd's calendar format can't express every cron expression (steps and ranges like
`*/15`); for those, register with `--platform cron` to use crontab instead.

## Command reference

All commands are `/odin schedule <subcommand>`; under the hood they run
`scripts/hermod.py`, which you can also call directly (handy for CI/scripting):

| Command | What it does |
| --- | --- |
| `register <loop> "<cron>"` | Validate schedulability, acknowledge outward actions, write the declaration + a default profile. **No OS change.** |
| `install <loop>` | Generate and load the OS trigger (launchd plist / crontab line). |
| `list` | List schedules with cron, install status, and acknowledged outward actions. |
| `uninstall <loop>` | Unload the OS trigger; keep the declaration. |
| `remove <loop>` | Uninstall if installed, then delete the declaration + profile. |

The raw CLI mirrors these — e.g.
`python3 scripts/hermod.py register <loop> --cron "<expr>" --project-dir <root> --ack`,
and `… run <loop>` is the fire-time entry the OS trigger calls.

Everything a schedule needs lives under the gitignored `.odin-loop/schedules/`:

| File | Role |
| --- | --- |
| `<loop>.yaml` | the schedule: `loop`, `cron`, `settings_profile`, `platform`, `project_dir`, `log`, `created_at`, `enabled`, `outward_actions`, `notify` |
| `<loop>.settings.json` | the scoped permission profile for the unattended run |
| `<loop>.log` | one line per fire (start, re-check, exit / refusal / skip) |
| `<loop>.lock` | the overlap guard (PID + run id) |

## Troubleshooting

- **It didn't run.** Read `.odin-loop/schedules/<loop>.log`. launchd and cron run with a
  **minimal PATH**, so `claude`/`gh`/`git` must be resolvable; a missing binary is
  logged as a loud failure rather than a silent no-op.
- **It was skipped.** A previous run still held `.odin-loop/schedules/<loop>.lock`.
  Overlapping fires don't stack — the second one logs `skipped` and exits. A crashed
  run's stale lock (dead PID) is reclaimed automatically.
- **It was refused.** The fire-time re-check found the loop is no longer schedulable
  (it gained a human gate / interview). The log names the offending stage; fix the loop
  or re-author the autonomous variant.
- **Auth expired.** The headless run uses your `claude` login; if the token expired the
  failure shows in the log. Re-authenticate and the next tick proceeds.

## See also

- [Authoring custom loops](authoring-loops.md) — write the loop you want to schedule.
- [Features](features.md) — every `/odin` command, including `schedule`.
- [Design](design.md) — the loop-as-data model, gates, and the Norse architecture.
