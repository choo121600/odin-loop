---
name: hermod
description: >
  Hermóðr — the Odin-Loop scheduler. Registers a FULLY-AUTONOMOUS loop (one with no
  human gate) to run unattended on the OS scheduler (macOS launchd / crontab), and is
  the fire-time runner. Use whenever the user invokes /odin schedule (register | list |
  remove | install | uninstall), or asks to run a loop on a cron/schedule, automate a
  daily loop, or set up an unattended/overnight Odin-Loop run.
---

# Hermóðr — the scheduler (Óðinn's herald)

Hermóðr runs Odin's errands on a schedule. He takes a **fully-autonomous** loop — one
that never pauses for a human — and registers it with the OS scheduler so it fires
unattended, then drives `/odin run <loop>` headlessly each tick.

This preserves Odin-Loop's core rule — *humans hold the wheel at `ai+human` gates* —
**by construction**: only loops with **no human gate** are schedulable, so an
unattended run can never silently auto-approve a checkpoint. Because "no human gate" is
necessary but **not sufficient** for safety (an all-`ai` loop can still merge PRs or
ship code), registration also makes the loop's **blast radius explicit** and contains
the run behind a scoped Claude settings profile.

All deterministic work — schedulability, cron validation, outward-action detection,
profile/plist/crontab generation, locking, the fire-time runner — lives in
`${CLAUDE_PLUGIN_ROOT}/scripts/hermod.py`. This skill is the **UX + judgment**: it
shells out to that script and handles the acknowledgment and refusal conversations.

## Where things live

| Thing                  | Path                                            |
| ---------------------- | ----------------------------------------------- |
| Schedule declarations  | `<project>/.odin-loop/schedules/<loop>.yaml`    |
| Per-schedule profile   | `<project>/.odin-loop/schedules/<loop>.settings.json` |
| Per-schedule run log   | `<project>/.odin-loop/schedules/<loop>.log`     |
| Lock (overlap guard)   | `<project>/.odin-loop/schedules/<loop>.lock`    |
| OS trigger (macOS)     | `~/Library/LaunchAgents/com.odin-loop.hermod.<loop>.plist` |

`.odin-loop/` is gitignored — schedules, profiles, locks, and logs never enter a commit.

Two-step by design: **`register` writes data only**; **`install` performs the OS
wiring**. So a schedule can be reviewed before anything touches launchd/cron.

---

## `/odin schedule register <loop> "<cron>"`

Declare a schedule. **Validate, surface the blast radius, get acknowledgment, then
write** — in this order:

1. **Resolve the loop** (project `.odin-loop/loops/` first, then built-in `loops/`).
2. **Schedulability gate.** Run:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_loop.py" --schedulable <loop.yaml>
   ```
   Exit `1` means the loop has an `ai+human`/`human` gate or a `deep` interview — it is
   **not schedulable**. Do NOT register it. Report the named violations and the escape
   hatch:
   > `<loop>` 은 사람 게이트가 있어 무인 스케줄이 불가합니다 (`<stage>`: `<mode>`).
   > 무인용으로 쓰려면 **autonomous 변종을 작성**하세요 — 모든 게이트를 `ai`로, deep
   > 인터뷰 없이 (`/odin new`, 또는 사람 게이트를 `ai`로 낮춘 복사본). 사람 게이트를
   > 떼면 그 자리를 메우던 안전망이 사라지니, 주변 `ai` 게이트를 함께 조이세요.
3. **Blast-radius acknowledgment.** Show the loop's outward-facing actions and require
   an **explicit yes** before writing:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hermod.py" register <loop> \
     --cron "<expr>" --project-dir "<abs project root>" [--platform auto|launchd|cron] \
     [--notify off|on-failure|always]
   ```
   `--notify` (default `on-failure`) sets the desktop-notification policy for the
   unattended run — `on-failure` notifies on `error`/`refused`, `always` on every fire,
   `off` never. Best-effort (osascript / notify-send); a notify failure never breaks the run.
   The script re-detects the actions and **refuses without `--ack`**. Present them —
   e.g. *"이 루프는 무인으로 `git push` · `gh pr create` · `gh pr merge` 를 수행합니다.
   허용하시겠어요?"* — and only on a clear yes, re-run with `--ack`.
4. On success the script writes `<loop>.yaml` + a **conservative** `<loop>.settings.json`
   (Read/Write/Edit + only the scoped `Bash(git:*)`/`Bash(gh:*)` the loop needs — never
   blanket Bash, never `--dangerously-skip-permissions`). Tell the user they may edit the
   profile to tighten/widen it, and offer to `install`.

A bad cron expression is rejected (`register` exits 1). Capture the **absolute** project
root for `--project-dir` — the headless trigger `cd`s there before running.

## `/odin schedule install <loop>`

Generate the OS trigger from the declaration and load it:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hermod.py" install <loop> --project-dir "<root>"
```
macOS → a LaunchAgent plist + `launchctl bootstrap`; Linux (or `platform: cron`) → a
crontab entry. The trigger runs `claude -p "/odin run <loop>" --settings <profile>`
under a full PATH, guarded by a lock and logged to `<loop>.log`. Report where it landed.

> The real overnight fire and the `launchctl`/`crontab` load are environment-dependent;
> confirm the first fire by checking `<loop>.log`, not by assuming.

## `/odin schedule list`

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hermod.py" list --project-dir "<root>"
```
Print each schedule: loop, cron, platform, install status, the **acknowledged outward
actions** (so the blast radius stays visible), and its **runtime health** — `last_fire`
(time + outcome, or `never`), `recent_failures`, and `next_fire` (next run time from the
cron). The `last_fire`/`recent_failures` come from `<loop>.log`; all are best-effort
(a missing log just shows `never`).

## `/odin schedule remove <loop>` / `uninstall <loop>`

`uninstall` unloads the OS trigger (`launchctl bootout` / crontab edit) and removes the
plist — leaving nothing behind. `remove` deletes the declaration + profile. Removing a
never-installed schedule is a clean no-op on the OS side.

## The fire-time runner (what the OS calls)

The trigger invokes `hermod.py run <loop>`, which:
1. takes the lock (`<loop>.lock`); a live previous run → **skip**, don't stack;
2. **re-validates schedulability** — if the loop has since gained a human gate or deep
   interview, it **refuses and logs**, never running into a pause;
3. runs `claude -p "/odin run <loop>" --settings <profile>`;
4. appends the outcome to `<loop>.log`; a missing `claude`/`gh`/`git` fails loudly.

---

## Principles (do not violate)

- **Only fully-autonomous loops schedule.** Never bypass the `--schedulable` gate; a
  human-gated loop must be refused, with the autonomous-variant escape hatch.
- **Never auto-acknowledge the blast radius.** Outward actions need an explicit human yes.
- **Never widen permissions to a bypass.** The settings profile is the containment;
  `--dangerously-skip-permissions` is forbidden for a scheduled run.
- **Register is data; install is side effects.** Keep the two steps separate.
- **The runner re-checks at every fire.** Registration-time approval is not a forever pass.
