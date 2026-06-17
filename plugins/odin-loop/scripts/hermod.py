#!/usr/bin/env python3
"""
hermod.py — Hermóðr, the Odin-Loop scheduler (Óðinn's herald, who runs his errands).

Registers a FULLY-AUTONOMOUS loop (one with no human gate) to run unattended on the
OS scheduler (macOS launchd / crontab), and is itself the fire-time runner.

Design rules (see the run's spec.md):
  - Only schedulable loops (`validate_loop.schedulable_violations(doc) == []`) may be
    registered, and the runner RE-VALIDATES on every fire — a loop that gains a human
    gate after registration is refused, never driven into a pause.
  - Outward-facing actions (git push / gh pr / gh issue …) are detected and must be
    explicitly acknowledged at register; the unattended run is contained by a scoped
    Claude settings profile (NOT `--dangerously-skip-permissions`).
  - A lock prevents overlapping fires; every fire is logged.

CLI (the `hermod` skill shells out to this):
    hermod.py register <loop> --cron "<expr>" --project-dir <dir> [--ack] [--platform ...]
    hermod.py list | remove <loop> | install <loop> | uninstall <loop> | run <loop>

stdlib + PyYAML (same dependency as validate_loop.py).
"""
import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys

try:
    import yaml
except Exception:
    yaml = None

import validate_loop  # sibling module — provides schedulable_violations()


# Loop names become file paths AND shell / launchd arguments — constrain them hard
# (a name like `a"; rm -rf …; "` would otherwise inject shell in the crontab path).
_LOOP_NAME_RE = re.compile(r"[A-Za-z0-9._-]+")


def _check_name(loop_name):
    # fullmatch (not match+`$`): `$` would let a trailing-newline name slip through.
    if not (isinstance(loop_name, str) and _LOOP_NAME_RE.fullmatch(loop_name)):
        raise ValueError("invalid loop name %r — must match [A-Za-z0-9._-]+ "
                         "(it becomes a file path and a shell/launchd argument)"
                         % (loop_name,))
    return loop_name


# ============================================================ cron ==============
_CRON_RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]


def _valid_cron_field(field, lo, hi):
    """One cron field: a comma list of `*`, `*/n`, `a`, `a-b`, or `a-b/n`."""
    for part in field.split(","):
        if part == "":
            return False
        base = part
        if "/" in part:
            base, _, step = part.partition("/")
            if not step.isdigit() or int(step) == 0:
                return False
        if base == "*":
            continue
        if "-" in base:
            a, _, b = base.partition("-")
            if not (a.isdigit() and b.isdigit()):
                return False
            if int(a) > int(b) or int(a) < lo or int(b) > hi:
                return False
        elif base.isdigit():
            if int(base) < lo or int(base) > hi:
                return False
        else:
            return False
    return True


def valid_cron(expr):
    """True iff `expr` is a standard 5-field cron expression with in-range values."""
    if not isinstance(expr, str):
        return False
    fields = expr.split()
    if len(fields) != 5:
        return False
    return all(_valid_cron_field(f, lo, hi)
               for f, (lo, hi) in zip(fields, _CRON_RANGES))


# ================================================ outward-action detection ======
_OUTWARD_PATTERNS = [
    ("git push", r"git\s+push"),
    ("gh pr create", r"gh\s+pr\s+create"),
    ("gh pr merge", r"gh\s+pr\s+merge"),
    ("gh issue create", r"gh\s+issue\s+create"),
    ("gh release create", r"gh\s+release\s+create"),
    ("board move", r"gh\s+project\s+item-edit"),
]


def detect_outward_actions(loop_doc):
    """Outward-facing (network / state-mutating) actions a loop's stage prompts
    perform. Heuristic text scan, biased to over-warn — the settings profile is the
    hard containment. Returns a sorted, unique list of canonical labels."""
    text = ""
    if isinstance(loop_doc, dict):
        for st in loop_doc.get("stages", []) or []:
            if isinstance(st, dict):
                text += "\n%s\n%s" % (st.get("prompt", ""), st.get("goal", ""))
    return sorted({label for label, pat in _OUTWARD_PATTERNS
                   if re.search(pat, text, re.I)})


# ===================================================== settings profile =========
# Command binaries a scheduled run may legitimately need, granted as scoped Bash.
# Deliberately only tokens that essentially never appear as English prose — ambiguous
# words like `go` / `make` / `python` would false-positive on "GO DEEP" / "make the
# edit" and OVER-grant, defeating "conservative". The user widens for anything else.
_PROFILE_TOOLS = ("git", "gh", "pytest", "npm", "python3")


def default_settings_profile(loop_doc):
    """A conservative, narrow Claude settings profile for the unattended run:
    Read/Write/Edit + ONLY scoped Bash for the command binaries the loop's stage
    prompts actually invoke (so the run can do its job without blanket Bash). Never a
    permission bypass. Errs narrow — the user may widen it if a needed tool is missing."""
    allow = ["Read", "Write", "Edit", "Glob", "Grep"]
    text = ""
    if isinstance(loop_doc, dict):
        for st in loop_doc.get("stages", []) or []:
            if isinstance(st, dict):
                text += " %s %s" % (st.get("prompt", ""), st.get("goal", ""))
    for tool in _PROFILE_TOOLS:
        if re.search(r"\b%s\b" % re.escape(tool), text):
            allow.append("Bash(%s:*)" % tool)
    return {"permissions": {"allow": allow, "deny": ["Bash(rm:*)", "Bash(sudo:*)"]}}


# ======================================================= schedule store =========
def _now(now=None):
    return now or _dt.datetime.now().isoformat(timespec="seconds")


def _schedules_dir(project_dir=None, schedules_dir=None):
    if schedules_dir:
        return schedules_dir
    return os.path.join(project_dir or os.getcwd(), ".odin-loop", "schedules")


def schedule_path(loop_name, schedules_dir):
    return os.path.join(schedules_dir, "%s.yaml" % loop_name)


def register(loop_name, loop_doc, cron, ack, project_dir, schedules_dir,
             platform="auto", notify="on-failure", now=None):
    """Validate + write a schedule declaration (data only — no OS install).

    Raises ValueError, writing NOTHING, on: a non-schedulable loop (has a human gate
    / deep interview), an invalid cron expression, or un-acknowledged outward actions.
    """
    _check_name(loop_name)
    if notify not in _NOTIFY_VALUES:
        raise ValueError("invalid notify %r — one of %s" % (notify, _NOTIFY_VALUES))
    violations = validate_loop.schedulable_violations(loop_doc)
    if violations:
        raise ValueError("loop `%s` is not schedulable (it pauses for a human):\n  - %s"
                         "\nAuthor an autonomous variant (every gate `ai`, no deep "
                         "interview) to schedule it."
                         % (loop_name, "\n  - ".join(violations)))
    if not valid_cron(cron):
        raise ValueError("invalid cron expression: %r (expected 5 fields)" % (cron,))
    actions = detect_outward_actions(loop_doc)
    if actions and not ack:
        raise ValueError("loop `%s` performs outward-facing actions that would run "
                         "UNATTENDED:\n  - %s\nRe-run with acknowledgment to accept them."
                         % (loop_name, "\n  - ".join(actions)))

    os.makedirs(schedules_dir, exist_ok=True)
    profile_path = os.path.join(schedules_dir, "%s.settings.json" % loop_name)
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(default_settings_profile(loop_doc), f, indent=2)
    schedule = {
        "loop": loop_name,
        "cron": cron,
        "settings_profile": profile_path,
        "platform": platform,
        "project_dir": project_dir,
        "log": os.path.join(schedules_dir, "%s.log" % loop_name),
        "created_at": _now(now),
        "enabled": True,
        "outward_actions": actions,
        "notify": notify,
    }
    with open(schedule_path(loop_name, schedules_dir), "w", encoding="utf-8") as f:
        yaml.safe_dump(schedule, f, sort_keys=False)
    return schedule


# ===================================================== schedule status ==========
# Read-only enrichment of `list`: last fire (from the log), recent failures, and next
# fire (from the cron). All best-effort — a missing/malformed log never raises.
_OUTCOME_VERBS = {"ran": "ran", "error": "error", "refused": "refused",
                  "skipped": "skipped-locked"}
_LOG_LINE_RE = re.compile(r"^\[([^\]]+)\]\s+(\S+)\s*(.*)$")


def _parse_outcome_line(line):
    m = _LOG_LINE_RE.match(line.strip())
    if not m:
        return None
    status = _OUTCOME_VERBS.get(m.group(2).rstrip(":"))
    if status is None:
        return None  # e.g. a `notify failed …` line — not a fire outcome
    return {"at": m.group(1), "status": status, "reason": m.group(3).strip() or None}


def _outcome_lines(log_path):
    try:
        with open(log_path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeError):
        return []
    return [o for o in (_parse_outcome_line(ln) for ln in text.splitlines()) if o]


def last_outcome(log_path):
    """The last real fire outcome in the log (ignoring `notify failed` lines), or None
    if the log is missing / empty / unparseable. Best-effort — never raises."""
    outs = _outcome_lines(log_path)
    return outs[-1] if outs else None


def recent_failures(log_path, n=10):
    """Count of `error`/`refused` among the last `n` fire outcomes (0 if none / no log)."""
    return sum(1 for o in _outcome_lines(log_path)[-n:]
               if o["status"] in ("error", "refused"))


def _cron_field_set(field, lo, hi):
    """Expand one cron field (`*`, `*/n`, `a-b`, `a-b/n`, comma lists) to its values."""
    vals = set()
    for part in field.split(","):
        base, step = part, 1
        if "/" in part:
            base, _, step_s = part.partition("/")
            step = int(step_s)
        if base == "*":
            start, end = lo, hi
        elif "-" in base:
            a, _, b = base.partition("-")
            start, end = int(a), int(b)
        else:
            start = end = int(base)
        vals.update(range(start, end + 1, step))
    return vals


def next_fire(cron, after, _cap_days=366):
    """The next datetime strictly after `after` matching the 5-field cron (system local
    time), reusing the cron grammar. Bounded search → None if nothing matches in the
    window. `after` is injected, so the result is deterministic (no wall clock)."""
    if not valid_cron(cron):
        return None
    fmin, fhour, fdom, fmonth, fdow = cron.split()
    minutes = _cron_field_set(fmin, 0, 59)
    hours = _cron_field_set(fhour, 0, 23)
    doms = _cron_field_set(fdom, 1, 31)
    months = _cron_field_set(fmonth, 1, 12)
    dows = _cron_field_set(fdow, 0, 7)
    dom_r, dow_r = fdom != "*", fdow != "*"
    t = after.replace(second=0, microsecond=0) + _dt.timedelta(minutes=1)
    limit = after + _dt.timedelta(days=_cap_days)
    while t <= limit:
        if t.minute in minutes and t.hour in hours and t.month in months:
            cron_dow = (t.weekday() + 1) % 7           # cron: Sun=0/7, Mon=1 … Sat=6
            dow_ok = cron_dow in dows or (7 in dows and cron_dow == 0)
            # standard cron quirk: when BOTH dom and dow are restricted, match is OR
            if dom_r and dow_r:
                day_ok = (t.day in doms) or dow_ok
            elif dom_r:
                day_ok = t.day in doms
            elif dow_r:
                day_ok = dow_ok
            else:
                day_ok = True
            if day_ok:
                return t
        t += _dt.timedelta(minutes=1)
    return None


def list_schedules(schedules_dir, agents_dir=None, now=None):
    if not os.path.isdir(schedules_dir):
        return []
    now = now or _dt.datetime.now()
    out = []
    for fn in sorted(os.listdir(schedules_dir)):
        if fn.endswith(".yaml"):
            with open(os.path.join(schedules_dir, fn), encoding="utf-8") as f:
                item = yaml.safe_load(f)
            item["installed"] = is_installed(item, agents_dir)            # criterion 10
            log = item.get("log") or _log_path(item)
            item["last_fire"] = last_outcome(log)                          # criteria 5, 1
            item["recent_failures"] = recent_failures(log)                 # criterion 2
            item["next_fire"] = next_fire(item.get("cron", ""), now)       # criterion 3
            out.append(item)
    return out


def remove(loop_name, schedules_dir, agents_dir=None, run=None):
    """Delete a schedule — first UNINSTALLING its OS trigger if installed, so nothing
    keeps firing against a removed declaration (criterion 11)."""
    sp = schedule_path(loop_name, schedules_dir)
    if os.path.isfile(sp):
        sched = yaml.safe_load(open(sp, encoding="utf-8"))
        if is_installed(sched, agents_dir):
            uninstall(sched, agents_dir=agents_dir, run=run)
    for suffix in (".yaml", ".settings.json"):
        p = os.path.join(schedules_dir, "%s%s" % (loop_name, suffix))
        if os.path.exists(p):
            os.remove(p)


# ===================================================== trigger rendering ========
def _scripts_dir():
    return os.path.dirname(os.path.abspath(__file__))


# A broad PATH so launchd/cron's minimal environment can resolve claude / gh / git —
# including the user bin dirs (e.g. ~/.local/bin) where `claude` is commonly installed.
_FULL_PATH = ":".join([
    os.path.expanduser("~/.local/bin"), os.path.expanduser("~/bin"),
    "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin",
])


def _resolve_claude(path=None):
    """Absolute path to the `claude` binary (searched on the broad PATH above, incl.
    ~/.local/bin), or bare `claude` as a fallback. Resolving here means a scheduled run
    finds claude even under launchd/cron's minimal environment — the gap an end-to-end
    fire surfaced (claude lived in ~/.local/bin, which the trigger PATH had omitted)."""
    return shutil.which("claude", path=path or _FULL_PATH) or "claude"


def _log_path(schedule):
    return schedule.get("log") or os.path.join(
        schedule["project_dir"], ".odin-loop", "schedules", "%s.log" % schedule["loop"])


def claude_command(schedule):
    """argv for the unattended headless run — scoped by a settings profile, NEVER a
    permission bypass."""
    _check_name(schedule["loop"])
    return [_resolve_claude(), "-p", "/odin-loop:odin run %s" % schedule["loop"],
            "--settings", schedule["settings_profile"]]


def _cron_to_calendar(cron):
    """Best-effort cron → launchd StartCalendarInterval (only plain numeric fields;
    launchd can't express steps/ranges — those fall back to crontab)."""
    cal = {}
    for key, val in zip(["Minute", "Hour", "Day", "Month", "Weekday"], cron.split()):
        if val.isdigit():
            cal[key] = int(val)
    return cal


def render_launchd_plist(schedule):
    loop = _check_name(schedule["loop"])
    runner = os.path.join(_scripts_dir(), "hermod.py")
    log = _log_path(schedule)
    cal = "".join("<key>%s</key><integer>%d</integer>" % (k, v)
                  for k, v in _cron_to_calendar(schedule["cron"]).items())
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0">\n<dict>\n'
            '  <key>Label</key><string>com.odin-loop.hermod.%s</string>\n'
            '  <key>ProgramArguments</key>\n  <array>\n'
            '    <string>python3</string><string>%s</string>'
            '<string>run</string><string>%s</string>\n  </array>\n'
            '  <key>WorkingDirectory</key><string>%s</string>\n'
            '  <key>EnvironmentVariables</key>\n'
            '  <dict><key>PATH</key><string>%s</string></dict>\n'
            '  <key>StartCalendarInterval</key>\n  <dict>%s</dict>\n'
            '  <key>StandardOutPath</key><string>%s</string>\n'
            '  <key>StandardErrorPath</key><string>%s</string>\n'
            '</dict>\n</plist>\n'
            % (loop, runner, loop, schedule["project_dir"], _FULL_PATH, cal, log, log))


def render_crontab_entry(schedule):
    loop = _check_name(schedule["loop"])
    runner = os.path.join(_scripts_dir(), "hermod.py")
    return ("%s cd %s && PATH=%s python3 %s run %s >> %s 2>&1"
            % (schedule["cron"], schedule["project_dir"], _FULL_PATH,
               runner, loop, _log_path(schedule)))


# ============================================================ lock ==============
def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except (ValueError, TypeError, OverflowError):
        return False
    return True


def acquire_lock(lock_path, run_id="hermod"):
    """Acquire an exclusive run lock. Returns False if a LIVE process holds it;
    reclaims a stale (dead-PID) or corrupt lock and returns True."""
    if os.path.exists(lock_path):
        try:
            held = json.load(open(lock_path, encoding="utf-8"))
            if pid_alive(held.get("pid")):
                return False
        except Exception:
            pass  # corrupt → treat as stale
    with open(lock_path, "w", encoding="utf-8") as f:
        json.dump({"pid": os.getpid(), "run": run_id}, f)
    return True


def release_lock(lock_path):
    try:
        os.remove(lock_path)
    except FileNotFoundError:
        pass


# ========================================================= fire-time ============
def _log(log_path, msg, now=None):
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("[%s] %s\n" % (_now(now), msg))


def _default_spawn(cmd):
    return subprocess.call(cmd)


# ========================================================= notification =========
# A scheduled run only logs its outcome; `notify` adds an opt-in desktop heads-up so a
# failing overnight run is noticed. It is best-effort and NEVER changes the run.
_NOTIFY_VALUES = ("off", "on-failure", "always")


def _should_notify(policy, status):
    """Whether a terminal `status` should notify under `policy`. `on-failure` = the
    genuine problems {error, refused}; `skipped-locked` is a benign overlap, not a
    failure. `off` / anything unknown → never."""
    if policy == "always":
        return True
    if policy == "on-failure":
        return status in ("error", "refused")
    return False


def _applescript_str(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _notify_command(loop, status, reason=None):
    """OS-native notification argv — no third-party dependency. Names the loop, the
    outcome, and (on error/refusal) a one-line reason."""
    title = "Odin-Loop · %s" % loop
    body = "schedule %s: %s" % (loop, status)
    if reason:
        body += " — %s" % reason
    if sys.platform == "darwin":
        return ["osascript", "-e", "display notification %s with title %s"
                % (_applescript_str(body), _applescript_str(title))]
    return ["notify-send", title, body]


def notify(schedule, outcome, notifier=None, log_path=None, now=None):
    """Best-effort, NON-FATAL heads-up on a terminal outcome, per the schedule's
    `notify` policy (default `on-failure`). A notify failure (missing binary, no GUI
    session) is caught + logged and never changes the run's outcome or exit status."""
    policy = (schedule or {}).get("notify", "on-failure")
    status = (outcome or {}).get("status", "?")
    if not _should_notify(policy, status):
        return False
    loop = (outcome or {}).get("loop") or (schedule or {}).get("loop", "?")
    reason = outcome.get("error") or ("; ".join(outcome.get("violations", []) or []) or None)
    notifier = notifier or _default_spawn
    try:
        notifier(_notify_command(loop, status, reason))
        return True
    except Exception as e:  # best-effort: a notify failure must never break the run
        if log_path:
            _log(log_path, "notify failed (best-effort): %s" % e, now)
        return False


def fire(schedule, loop_doc, lock_path, log_path, spawn=None, notifier=None, now=None):
    """The fire-time runner launchd/cron invokes: lock → re-validate schedulability →
    run claude headless → log → notify. Returns an outcome dict (status: ran | refused |
    error | skipped-locked)."""
    spawn = spawn or _default_spawn
    loop = schedule.get("loop", "?")

    def _finish(outcome):
        # best-effort notify on every terminal outcome; never affects the result
        notify(schedule, outcome, notifier=notifier, log_path=log_path, now=now)
        return outcome

    if not acquire_lock(lock_path, run_id=loop):
        _log(log_path, "skipped: a previous run of `%s` still holds the lock" % loop, now)
        return _finish({"status": "skipped-locked", "loop": loop})
    try:
        violations = validate_loop.schedulable_violations(loop_doc)
        if violations:
            _log(log_path, "refused: `%s` is no longer schedulable: %s"
                 % (loop, "; ".join(violations)), now)
            return _finish({"status": "refused", "loop": loop, "violations": violations})
        try:
            rc = spawn(claude_command(schedule))
        except FileNotFoundError as e:
            _log(log_path, "error: could not run claude — binary not found (%s)" % e, now)
            return _finish({"status": "error", "loop": loop, "error": str(e)})
        _log(log_path, "ran `%s` (exit %s)" % (loop, rc), now)
        return _finish({"status": "ran", "loop": loop, "exit": rc})
    finally:
        release_lock(lock_path)


# ======================================================= install / uninstall ====
def _agents_dir(agents_dir=None):
    return agents_dir or os.path.expanduser("~/Library/LaunchAgents")


def _use_launchd(schedule):
    platform = schedule.get("platform", "auto")
    return platform == "launchd" or (platform == "auto" and sys.platform == "darwin")


def _plist_path(loop, agents_dir):
    return os.path.join(_agents_dir(agents_dir), "com.odin-loop.hermod.%s.plist" % loop)


def is_installed(schedule, agents_dir=None):
    """Whether this schedule's OS trigger is currently present (criterion 10)."""
    if _use_launchd(schedule):
        return os.path.exists(_plist_path(schedule["loop"], agents_dir))
    try:
        out = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
    except (FileNotFoundError, OSError):
        return False
    return ("hermod.py run %s" % schedule["loop"]) in out


def _crontab_lines():
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        return r.stdout.splitlines() if r.returncode == 0 else []
    except (FileNotFoundError, OSError):
        return []


def _write_crontab(lines):
    # No shell: filtered lines go straight to `crontab -` via stdin (injection-proof).
    subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True)


def install(schedule, agents_dir=None, run=None):
    """Render the trigger and load it onto the OS scheduler. `run` is the launchd
    command runner (injectable for tests)."""
    run = run or _default_spawn
    loop = _check_name(schedule["loop"])
    if _use_launchd(schedule):
        ad = _agents_dir(agents_dir)
        os.makedirs(ad, exist_ok=True)
        plist = _plist_path(loop, agents_dir)
        with open(plist, "w", encoding="utf-8") as f:
            f.write(render_launchd_plist(schedule))
        run(["launchctl", "bootstrap", "gui/%d" % os.getuid(), plist])
        return plist
    entry = render_crontab_entry(schedule)
    marker = "hermod.py run %s" % loop
    _write_crontab([ln for ln in _crontab_lines() if marker not in ln] + [entry])
    return entry


def uninstall(schedule, agents_dir=None, run=None):
    """Unload the trigger and remove it — leaving nothing behind."""
    run = run or _default_spawn
    loop = _check_name(schedule["loop"])
    if _use_launchd(schedule):
        run(["launchctl", "bootout",
             "gui/%d/com.odin-loop.hermod.%s" % (os.getuid(), loop)])
        plist = _plist_path(loop, agents_dir)
        if os.path.exists(plist):
            os.remove(plist)
        return
    marker = "hermod.py run %s" % loop
    _write_crontab([ln for ln in _crontab_lines() if marker not in ln])


# ============================================================ CLI ===============
def _load_loop_doc(loop_name, project_dir):
    for cand in (os.path.join(project_dir, ".odin-loop", "loops", "%s.yaml" % loop_name),
                 os.path.join(_scripts_dir(), "..", "loops", "%s.yaml" % loop_name)):
        if os.path.isfile(cand):
            return yaml.safe_load(open(cand, encoding="utf-8"))
    raise FileNotFoundError("loop `%s` not found (project or built-in loops)" % loop_name)


def _cli(argv=None):
    ap = argparse.ArgumentParser(description="Hermóðr — schedule autonomous Odin-Loop loops")
    sub = ap.add_subparsers(dest="cmd", required=True)
    reg = sub.add_parser("register", help="declare a schedule (validates; no OS install)")
    reg.add_argument("loop")
    reg.add_argument("--cron", required=True)
    reg.add_argument("--project-dir", default=os.getcwd())
    reg.add_argument("--platform", default="auto", choices=["auto", "launchd", "cron"])
    reg.add_argument("--ack", action="store_true", help="acknowledge outward actions")
    reg.add_argument("--notify", default="on-failure",
                     choices=["off", "on-failure", "always"],
                     help="desktop notification policy for the unattended run")
    for name in ("remove", "install", "uninstall", "run"):
        p = sub.add_parser(name)
        p.add_argument("loop")
        p.add_argument("--project-dir", default=os.getcwd())
    lst = sub.add_parser("list")
    lst.add_argument("--project-dir", default=os.getcwd())
    args = ap.parse_args(argv)

    if yaml is None:
        print(json.dumps({"ok": False, "error": "PyYAML not installed"}))
        return 3

    sd = _schedules_dir(args.project_dir)

    if getattr(args, "loop", None) is not None:
        try:
            _check_name(args.loop)
        except ValueError as e:
            print(json.dumps({"ok": False, "error": str(e)}))
            return 1

    if args.cmd == "register":
        try:
            sched = register(args.loop, _load_loop_doc(args.loop, args.project_dir),
                             args.cron, args.ack, args.project_dir, sd, args.platform,
                             notify=args.notify)
        except (ValueError, FileNotFoundError) as e:
            print(json.dumps({"ok": False, "error": str(e)}))
            return 1
        print(json.dumps({"ok": True, "schedule": schedule_path(args.loop, sd),
                          "outward_actions": sched["outward_actions"]}, indent=2))
        return 0
    if args.cmd == "list":
        print(json.dumps({"schedules": list_schedules(sd)}, indent=2, default=str))
        return 0
    if args.cmd == "remove":
        remove(args.loop, sd)
        print(json.dumps({"ok": True}))
        return 0

    sp = schedule_path(args.loop, sd)
    if not os.path.isfile(sp):
        print(json.dumps({"ok": False, "error": "no schedule for `%s`" % args.loop}))
        return 1
    sched = yaml.safe_load(open(sp, encoding="utf-8"))
    if args.cmd == "install":
        print(json.dumps({"ok": True, "installed": str(install(sched))}, indent=2))
        return 0
    if args.cmd == "uninstall":
        uninstall(sched)
        print(json.dumps({"ok": True}))
        return 0
    if args.cmd == "run":
        out = fire(sched, _load_loop_doc(args.loop, args.project_dir),
                   os.path.join(sd, "%s.lock" % args.loop), _log_path(sched))
        print(json.dumps(out))
        return 0 if out["status"] in ("ran", "skipped-locked") else 1


if __name__ == "__main__":
    sys.exit(_cli())
