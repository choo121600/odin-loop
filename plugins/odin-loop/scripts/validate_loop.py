#!/usr/bin/env python3
"""
validate_loop.py — deterministic schema validator for Odin-Loop loop YAML.

Odin-Loop's engine is an LLM, so loop validation has always been "best effort"
prose in the loop-engine skill. This script makes the structural rules MECHANICAL:
the engine runs it before starting a run (and after `/odin new` writes a loop), so
a malformed loop is caught by code, not by remembering to check. It validates
DATA; it does not drive the loop — the "loop is data, not code" model is intact.

It emits a compact JSON report to stdout and signals the outcome via exit code:
    0  every loop valid (warnings may still be present)
    1  at least one loop has a blocking error
    2  usage error (no paths, unreadable file)
    3  cannot validate — PyYAML not installed (engine should fall back to its
       own prose checks; nothing is worse than today)

Usage:
    validate_loop.py <loop.yaml> [<loop.yaml> ...]

stdlib only, except PyYAML (degrades gracefully when absent).
"""
import argparse
import json
import os
import re
import sys

try:
    import yaml  # PyYAML — not stdlib; absence is handled (exit 3)
except Exception:
    yaml = None

GATE_MODES = ("ai", "ai+human", "human")
AGENT_VALUES = ("inline", "fresh")
ROLE_VALUES = ("explore", "planner", "executor", "critic", "reviewer")
# A role's default execution context. Override per-stage with `{role, fresh}`.
ROLE_DEFAULT_FRESH = {
    "explore": True, "planner": False, "executor": False,
    "critic": True, "reviewer": True,
}
CHALLENGE_RE = re.compile(r"^(contrarian|simplifier|ontologist)@\d+$")


def validate_loop(path, doc):
    """Return (errors, warnings) for one parsed loop document."""
    errors, warnings = [], []

    def err(m): errors.append(m)
    def warn(m): warnings.append(m)

    if not isinstance(doc, dict):
        return ["top level is not a mapping (expected a loop object)"], []

    # --- top-level fields ---
    name = doc.get("name")
    if not name or not isinstance(name, str):
        err("missing or non-string `name`")
    else:
        stem = os.path.splitext(os.path.basename(path))[0]
        if stem != name:
            warn(f"`name: {name}` does not match filename `{stem}` "
                 "(the engine resolves loops by filename)")

    if not isinstance(doc.get("version"), int):
        warn("`version` should be an integer (bump it on breaking edits)")
    if not doc.get("description"):
        warn("missing `description` (shown in `/odin list`)")

    mi = doc.get("max_iterations")
    if not isinstance(mi, int) or mi <= 0:
        err("`max_iterations` must be a positive integer")

    stages = doc.get("stages")
    if not isinstance(stages, list) or not stages:
        return errors + ["`stages` must be a non-empty list"], warnings

    # --- collect ids first (on_fail can point forward) ---
    ids = []
    for i, st in enumerate(stages):
        if not isinstance(st, dict):
            err(f"stage[{i}] is not a mapping")
            continue
        sid = st.get("id")
        if not sid or not isinstance(sid, str):
            err(f"stage[{i}] missing or non-string `id`")
        else:
            ids.append(sid)
    dupes = sorted({x for x in ids if ids.count(x) > 1})
    if dupes:
        err(f"duplicate stage id(s): {', '.join(dupes)}")
    idset = set(ids)

    # --- per-stage rules ---
    for st in stages:
        if not isinstance(st, dict):
            continue
        sid = st.get("id", "?")
        where = f"stage `{sid}`"

        # gate
        gate = st.get("gate")
        if not isinstance(gate, dict):
            err(f"{where}: missing `gate`")
        else:
            mode = gate.get("mode")
            if mode not in GATE_MODES:
                err(f"{where}: gate.mode must be one of {GATE_MODES} (got {mode!r})")
            if not (gate.get("check") and str(gate.get("check")).strip()):
                err(f"{where}: gate.check is empty")
            of = gate.get("on_fail")
            if of is not None and of not in idset:
                err(f"{where}: gate.on_fail `{of}` is not a real stage id")

        # agent — a string (`inline` | `fresh` | a role) or a `{role, fresh}` map.
        # We resolve it to one fact the rest of the rules care about: does this
        # stage run in a FRESH context (its own clean-room sub-agent)?
        agent = st.get("agent")
        effective_fresh = False
        if agent is None:
            pass
        elif isinstance(agent, str):
            if agent in AGENT_VALUES:
                effective_fresh = (agent == "fresh")
            elif agent in ROLE_VALUES:
                effective_fresh = ROLE_DEFAULT_FRESH[agent]
            else:
                err(f"{where}: agent must be `inline`, `fresh`, or a role "
                    f"{ROLE_VALUES} (got {agent!r})")
        elif isinstance(agent, dict):
            role = agent.get("role")
            if role not in ROLE_VALUES:
                err(f"{where}: agent.role must be one of {ROLE_VALUES} (got {role!r})")
            fr = agent.get("fresh")
            if fr is None:
                effective_fresh = ROLE_DEFAULT_FRESH.get(role, False)
            elif isinstance(fr, bool):
                effective_fresh = fr
            else:
                err(f"{where}: agent.fresh must be true/false (got {fr!r})")
            extra = set(agent) - {"role", "fresh"}
            if extra:
                warn(f"{where}: unknown agent key(s): {', '.join(sorted(extra))}")
        else:
            err(f"{where}: agent must be a string or a {{role, fresh}} mapping")

        if effective_fresh:
            consumes = st.get("consumes")
            if not (isinstance(consumes, list) and consumes):
                err(f"{where}: a fresh stage requires a non-empty `consumes` "
                    "(its only input channel)")

        # interview block (deep-interview playbook opt-in)
        iv = st.get("interview")
        if iv is not None:
            if not isinstance(iv, dict):
                err(f"{where}: `interview` must be a mapping")
            else:
                mode = iv.get("mode")
                # The rules below encode the deep-interview playbook's contract,
                # so they apply ONLY to `interview.mode: deep` (matching SKILL.md,
                # which scopes them to "any stage with interview.mode: deep"). A
                # non-deep block gets the unknown-mode warning but not these — see
                # issue #39.
                if mode != "deep":
                    warn(f"{where}: interview.mode `{mode!r}` is unknown "
                         "(only `deep` is supported today)")
                else:
                    if effective_fresh:
                        err(f"{where}: a deep interview talks to the user — it cannot "
                            "run in a fresh context")
                    produces = st.get("produces")
                    if not isinstance(produces, list):
                        err(f"{where}: a deep interview's `produces` must be a list "
                            "(otherwise the interview-log.md rule degrades to a "
                            "substring test and a scalar silently passes)")
                    elif "interview-log.md" not in produces:
                        err(f"{where}: a deep interview must list `interview-log.md` "
                            "in `produces` (the convergence ledger the gate reads)")
                    thr = iv.get("threshold")
                    if thr is not None and not (isinstance(thr, (int, float))
                                                and 0 < thr < 1):
                        err(f"{where}: interview.threshold must be a number in (0, 1) "
                            f"(got {thr!r})")
                    ch = iv.get("challenges")
                    if ch is not None:
                        if not isinstance(ch, list):
                            err(f"{where}: interview.challenges must be a list")
                        else:
                            for c in ch:
                                if not (isinstance(c, str) and CHALLENGE_RE.match(c)):
                                    err(f"{where}: bad challenge {c!r} "
                                        "(expected `contrarian|simplifier|ontologist@<round>`)")
                    aa = iv.get("auto_assist")
                    if aa is not None and not isinstance(aa, bool):
                        err(f"{where}: interview.auto_assist must be true/false")

    return errors, warnings


def schedulable_violations(doc):
    """Reasons a loop may NOT be scheduled to run unattended (Hermóðr), or [] if it
    is fully autonomous. A loop is schedulable iff EVERY gate is `ai` (no `ai+human`
    or `human`) and no stage runs a `deep` interview — i.e. it never pauses for a
    human. This preserves "humans hold the wheel at ai+human gates" by construction:
    only loops with no human gate can fire on a schedule. (Necessary, not sufficient,
    for safety — outward-action acknowledgment + a scoped settings profile handle the
    blast radius; see the hermod skill.)"""
    if not isinstance(doc, dict):
        return ["loop is not a mapping"]
    stages = doc.get("stages")
    if not isinstance(stages, list):
        return ["loop has no `stages` list"]
    out = []
    for st in stages:
        if not isinstance(st, dict):
            continue
        sid = st.get("id", "?")
        gate = st.get("gate")
        if isinstance(gate, dict) and gate.get("mode") in ("ai+human", "human"):
            out.append(f"stage `{sid}`: gate.mode `{gate.get('mode')}` needs a human "
                       "— an unattended run would block or silently auto-approve it")
        iv = st.get("interview")
        if isinstance(iv, dict) and iv:
            kind = ("interview.mode `deep`" if iv.get("mode") == "deep"
                    else "an `interview` stage")
            out.append("stage `%s`: %s interviews the user (ask/wait) — it cannot "
                       "run unattended" % (sid, kind))
    return out


def main():
    ap = argparse.ArgumentParser(description="Validate Odin-Loop loop YAML files.")
    ap.add_argument("paths", nargs="+", help="loop YAML file(s) to validate")
    ap.add_argument("--schedulable", action="store_true",
                    help="also require the loop be fully autonomous (no human gate / "
                         "deep interview), i.e. safe for Hermóðr to schedule unattended")
    args = ap.parse_args()

    if yaml is None:
        json.dump({
            "ok": None,
            "skipped": "PyYAML not installed; deterministic validation unavailable. "
                       "Install with `pip install pyyaml`, or fall back to manual checks.",
        }, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 3

    results, all_ok, usage_error = [], True, False
    for path in args.paths:
        if not os.path.isfile(path):
            results.append({"path": path, "ok": False,
                            "errors": ["file not found"], "warnings": []})
            all_ok = False
            usage_error = True
            continue
        try:
            doc = yaml.safe_load(open(path, encoding="utf-8"))
        except Exception as e:
            results.append({"path": path, "ok": False,
                            "errors": [f"YAML parse error: {e}"], "warnings": []})
            all_ok = False
            continue
        errors, warnings = validate_loop(path, doc)
        if args.schedulable:
            errors = errors + [f"not schedulable: {m}"
                               for m in schedulable_violations(doc)]
        ok = not errors
        all_ok = all_ok and ok
        results.append({
            "path": path,
            "loop": doc.get("name") if isinstance(doc, dict) else None,
            "ok": ok,
            "errors": errors,
            "warnings": warnings,
        })

    json.dump({"all_ok": all_ok, "results": results},
              sys.stdout, ensure_ascii=False, indent=2)
    print()
    if usage_error and all(not r["ok"] and r["errors"] == ["file not found"]
                           for r in results):
        return 2
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
