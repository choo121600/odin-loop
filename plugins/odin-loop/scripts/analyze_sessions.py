#!/usr/bin/env python3
"""
Muninn — session/run analyzer for Odin-Loop.

Reads (a) Odin-Loop run history (.odin-loop/runs/*/state.json) and
(b) raw Claude Code session transcripts (~/.claude/projects/<enc>/*.jsonl),
then emits a COMPACT JSON summary of workflow signals to stdout.

It deliberately emits only aggregate counts/patterns — never message content —
so the proposal step stays cheap and private. stdlib only; never loads a whole
transcript into memory (streams line by line).

Usage:
    analyze_sessions.py --cwd /path/to/project [--projects-root ~/.claude/projects]
                        [--runs-dir /path/to/.odin-loop/runs]
"""
import argparse, glob, json, os, sys
from collections import Counter, defaultdict

TEST_MARKERS = ("pytest", "jest", "vitest", "npm test", "npm run test",
                "go test", "cargo test", "unittest", "rspec", "phpunit",
                "ctest", "gradle test", "mvn test", "tox")
IMPL_TOOLS = ("Write", "Edit", "NotebookEdit")


def encode_cwd(cwd):
    # Claude Code encodes the project dir by replacing '/' and '.' with '-'.
    return "".join("-" if c in "/." else c for c in cwd)


def find_sessions_dir(projects_root, cwd):
    enc = encode_cwd(cwd)
    cand = os.path.join(projects_root, enc)
    if os.path.isdir(cand):
        return cand
    # fall back: pick the dir whose name best matches the cwd tail
    tail = encode_cwd(cwd).strip("-").split("-")[-1]
    matches = [d for d in glob.glob(os.path.join(projects_root, "*")) if tail in d]
    return matches[0] if matches else None


def analyze_runs(runs_dir):
    out = {
        "total_runs": 0, "completed": 0, "failed": 0, "abandoned": 0,
        "loops_used": Counter(),
        "stage_loopbacks": Counter(),     # times each stage was re-run (iterations-1)
        "gate_failures_by_stage": Counter(),
        "human_gate_count": 0, "ai_gate_count": 0,
    }
    if not runs_dir or not os.path.isdir(runs_dir):
        return _finalize_runs(out, found=False)
    for sf in glob.glob(os.path.join(runs_dir, "*", "state.json")):
        try:
            st = json.load(open(sf))
        except Exception:
            continue
        out["total_runs"] += 1
        status = st.get("status")
        if status == "done":
            out["completed"] += 1
        elif status == "failed":
            out["failed"] += 1
        else:
            out["abandoned"] += 1  # running/awaiting_approval = not finished
        if st.get("loop"):
            out["loops_used"][st["loop"]] += 1
        for stage, n in (st.get("iterations") or {}).items():
            if n and n > 1:
                out["stage_loopbacks"][stage] += (n - 1)
        for h in (st.get("history") or []):
            if h.get("result") == "fail":
                out["gate_failures_by_stage"][h.get("stage", "?")] += 1
            if h.get("gate") == "approved":
                out["human_gate_count"] += 1
            elif h.get("result") == "pass":
                out["ai_gate_count"] += 1
    return _finalize_runs(out, found=True)


def _finalize_runs(out, found):
    most_looped = out["stage_loopbacks"].most_common(1)
    return {
        "found_run_history": found,
        "total_runs": out["total_runs"],
        "completed": out["completed"],
        "failed": out["failed"],
        "abandoned": out["abandoned"],
        "loops_used": dict(out["loops_used"]),
        "stage_loopbacks": dict(out["stage_loopbacks"]),
        "most_looped_stage": most_looped[0][0] if most_looped else None,
        "gate_failures_by_stage": dict(out["gate_failures_by_stage"]),
        "human_gate_count": out["human_gate_count"],
        "ai_gate_count": out["ai_gate_count"],
    }


def analyze_sessions(sessions_dir):
    files = sorted(glob.glob(os.path.join(sessions_dir, "*.jsonl"))) if sessions_dir else []
    tool_usage = Counter()
    edit_files = Counter()           # file_path -> times edited/written
    impl_edits = 0
    test_runs = 0
    turns_before_first_impl = []     # per session
    sessions_with_impl = 0
    for f in files:
        turns = 0
        first_impl_seen = False
        try:
            fh = open(f, encoding="utf-8")
        except Exception:
            continue
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                msg = o.get("message")
                if not isinstance(msg, dict):
                    continue
                role = msg.get("role")
                if role in ("user", "assistant"):
                    if not first_impl_seen:
                        turns += 1
                content = msg.get("content")
                if not isinstance(content, list):
                    continue
                for c in content:
                    if not isinstance(c, dict) or c.get("type") != "tool_use":
                        continue
                    name = c.get("name", "?")
                    tool_usage[name] += 1
                    inp = c.get("input") or {}
                    if name in IMPL_TOOLS:
                        impl_edits += 1
                        fp = inp.get("file_path") or inp.get("notebook_path")
                        if fp:
                            edit_files[fp] += 1
                        if not first_impl_seen:
                            first_impl_seen = True
                            turns_before_first_impl.append(turns)
                            sessions_with_impl += 1
                    if name == "Bash":
                        cmd = (inp.get("command") or "").lower()
                        if any(m in cmd for m in TEST_MARKERS):
                            test_runs += 1
    distinct = len(edit_files)
    churn = round(impl_edits / distinct, 2) if distinct else 0.0
    reworked = {fp: n for fp, n in edit_files.items() if n >= 4}
    avg_turns = round(sum(turns_before_first_impl) / len(turns_before_first_impl), 1) \
        if turns_before_first_impl else None
    return {
        "session_count": len(files),
        "tool_usage": dict(tool_usage.most_common()),
        "impl_edits": impl_edits,
        "distinct_files_edited": distinct,
        "churn_ratio": churn,                       # edits per file; high = rework
        "heavily_reworked_files": len(reworked),    # files edited >=4 times
        "test_runs": test_runs,
        "avg_turns_before_first_edit": avg_turns,   # high = lots of pre-code back-and-forth
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--projects-root",
                    default=os.path.expanduser("~/.claude/projects"))
    ap.add_argument("--runs-dir", default=None)
    args = ap.parse_args()

    runs_dir = args.runs_dir or os.path.join(args.cwd, ".odin-loop", "runs")
    sessions_dir = find_sessions_dir(args.projects_root, args.cwd)

    report = {
        "cwd": args.cwd,
        "sessions_dir": sessions_dir,
        "runs_dir": runs_dir if os.path.isdir(runs_dir) else None,
        "odin_runs": analyze_runs(runs_dir),
        "sessions": analyze_sessions(sessions_dir),
        "heuristic_notes": [
            "churn_ratio = impl edits per distinct file; >2.5 suggests rework/underspecified work.",
            "most_looped_stage = where Odin-Loop runs loop back most; strengthen the gate BEFORE it.",
            "high avg_turns_before_first_edit in non-loop sessions = the interview stage would capture that deliberation up front.",
            "abandoned runs stuck at 'interview' may mean the interview is too long; consider a question cap.",
            "These are heuristics, not verdicts. Every proposal needs human approval.",
        ],
    }
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
