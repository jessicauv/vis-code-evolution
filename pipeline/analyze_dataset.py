"""
Step 1: Analyze the MOSAIC-agentic-3m dataset and produce findings.json.

Re-runnable: safe to run multiple times; overwrites findings.json each time.

Usage:
    python analyze_dataset.py
"""

import json
import os
import statistics
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from datasets import load_dataset

# ─── CONFIG ───────────────────────────────────────────────────────────────────
DATASET_NAME = "AISE-TUDelft/MOSAIC-agentic-3m"

# Agent names exactly as they appear in the dataset config (PullRequests_{AGENT})
AGENTS = ["Human", "Claude", "Codex", "Copilot", "Jules", "Devin"]

# Map dataset agent name → output key used in findings.json and image filenames
AGENT_KEY_MAP = {
    "Human":   "human",
    "Claude":  "claude_code",
    "Codex":   "codex",
    "Copilot": "copilot",
    "Jules":   "jules",
    "Devin":   "devin",
}

# Column names in the PullRequests_{agent} table
COL_ADDITIONS      = "additions"
COL_DELETIONS      = "deletions"
COL_MERGED_AT      = "merged_at"
COL_CREATED_AT     = "created_at"
COL_CLOSING_ISSUES = "closing_issues_count"
COL_FILES          = "files"
COL_PR_ID          = "id"

# Column names in the Commits_{agent} table (used for survival rate)
COMMIT_CONFIG_TEMPLATE = "Commits_{agent}"
COL_COMMIT_PR_ID   = "pr_id"
COL_COMMIT_DATE    = "authored_date"
COL_COMMIT_ADD     = "additions"
COL_COMMIT_DEL     = "deletions"

# Time windows (days) over which seed-commit line survival is measured
SURVIVAL_WINDOWS = [3, 7, 21]

OUTPUT_FILE = "findings.json"
# ──────────────────────────────────────────────────────────────────────────────


def parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def get_extensions(files_list: list) -> List[str]:
    """Extract lowercase file extensions from a list of file dicts or path strings."""
    exts = []
    for f in files_list or []:
        if isinstance(f, dict):
            path = f.get("path") or f.get("filename") or f.get("name") or ""
        else:
            path = str(f)
        _, ext = os.path.splitext(path)
        if ext:
            exts.append(ext.lower())
    return exts


def build_commit_lookup(agent_name: str) -> Dict[str, List]:
    """Stream Commits_{agent} and return {pr_id: [(authored_date, additions, deletions), ...]}."""
    config = COMMIT_CONFIG_TEMPLATE.format(agent=agent_name)
    print(f"  Loading {config} for survival rate …", flush=True)
    ds = load_dataset(DATASET_NAME, config, split="train", streaming=True)
    lookup: Dict[str, List] = {}
    for row in ds:
        pr_id = row.get(COL_COMMIT_PR_ID)
        if not pr_id:
            continue
        dt = parse_dt(row.get(COL_COMMIT_DATE))
        if dt is None:
            continue
        lookup.setdefault(pr_id, []).append((
            dt,
            row.get(COL_COMMIT_ADD) or 0,
            row.get(COL_COMMIT_DEL) or 0,
        ))
    return lookup


def analyze_agent(agent_name: str) -> Dict:
    commit_lookup = build_commit_lookup(agent_name)

    config = f"PullRequests_{agent_name}"
    print(f"  Loading {config} …", flush=True)
    ds = load_dataset(DATASET_NAME, config, split="train", streaming=True)

    pr_sizes: List[float]      = []
    merge_times: List[float]   = []
    survival_rates: List[float] = []
    merges    = 0
    total     = 0
    issue_linked = 0
    ext_counter: Counter = Counter()

    for row in ds:
        total += 1

        add = row.get(COL_ADDITIONS) or 0
        dlt = row.get(COL_DELETIONS) or 0
        pr_sizes.append(add + dlt)

        merged_at  = parse_dt(row.get(COL_MERGED_AT))
        created_at = parse_dt(row.get(COL_CREATED_AT))
        if merged_at:
            merges += 1
            if created_at:
                minutes = (merged_at - created_at).total_seconds() / 60
                if minutes >= 0:
                    merge_times.append(minutes)

        if (row.get(COL_CLOSING_ISSUES) or 0) > 0:
            issue_linked += 1

        # Survival rate: fraction of seed-commit additions not deleted within each time window
        pr_id = row.get(COL_PR_ID)
        pr_commits = commit_lookup.get(pr_id)
        if pr_commits:
            pr_commits_sorted = sorted(pr_commits, key=lambda x: x[0])
            seed_dt, seed_add, _ = pr_commits_sorted[0]
            if seed_add > 0:
                window_survivals = []
                for w_days in SURVIVAL_WINDOWS:
                    window_end = seed_dt + timedelta(days=w_days)
                    window_dels = sum(
                        c[2] for c in pr_commits_sorted[1:] if c[0] <= window_end
                    )
                    window_survivals.append(max(0.0, (seed_add - window_dels) / seed_add))
                survival_rates.append(statistics.mean(window_survivals))

        for ext in get_extensions(row.get(COL_FILES) or []):
            ext_counter[ext] += 1

        if total % 50_000 == 0:
            print(f"    … {total:,} rows processed", flush=True)

    top_file_types = [ext for ext, _ in ext_counter.most_common(5)]

    return {
        "total_prs":                  total,
        "median_pr_size":             round(statistics.median(pr_sizes), 2)        if pr_sizes        else 0,
        "merge_rate":                 round(merges / total, 4)                     if total           else 0,
        "median_merge_time_minutes":  round(statistics.median(merge_times), 2)     if merge_times     else 0,
        "issue_linking_rate":         round(issue_linked / total, 4)               if total           else 0,
        "survival_rate":              round(statistics.median(survival_rates), 4)  if survival_rates  else 0,
        "top_file_types":             top_file_types,
    }


def print_summary(findings: Dict) -> None:
    STAT_LABELS = [
        ("total_prs",                 "Total PRs",            "{:>10,.0f}"),
        ("median_pr_size",            "Median PR Size (lines)","{:>10.1f}"),
        ("merge_rate",                "Merge Rate",            "{:>10.1%}"),
        ("median_merge_time_minutes", "Merge Time (min)",      "{:>10.1f}"),
        ("issue_linking_rate",        "Issue Linking Rate",    "{:>10.1%}"),
        ("survival_rate",             "Survival Rate",         "{:>10.1%}"),
    ]

    agents = list(findings.keys())
    col_w  = 15
    label_w = 26

    # Header
    print("\n" + "=" * (label_w + col_w * len(agents) + 2))
    print(f"{'':>{label_w}}", end="")
    for a in agents:
        print(f"{a:>{col_w}}", end="")
    print()
    print("-" * (label_w + col_w * len(agents) + 2))

    # One row per numeric stat
    for key, label, fmt in STAT_LABELS:
        print(f"{label:<{label_w}}", end="")
        for a in agents:
            val = findings[a].get(key, 0)
            print(fmt.format(val), end="")
        print()

    # File types row
    print(f"{'Top File Types':<{label_w}}", end="")
    for a in agents:
        types = " ".join(findings[a].get("top_file_types", [])[:3])
        print(f"{types:>{col_w}}", end="")
    print()

    # Footer with per-stat min/max to help calibrate STAT_RANGES
    print("-" * (label_w + col_w * len(agents) + 2))
    print(f"{'[range  min → max]':<{label_w}}", end="")
    print()
    for key, label, fmt in STAT_LABELS:
        vals = [findings[a][key] for a in agents]
        lo, hi = min(vals), max(vals)
        print(f"  {label:<{label_w - 2}}" + fmt.format(lo) + "  →" + fmt.format(hi))
    print("=" * (label_w + col_w * len(agents) + 2))


def main() -> None:
    findings: Dict = {}
    for agent in AGENTS:
        key = AGENT_KEY_MAP[agent]
        print(f"\n[{agent}]")
        findings[key] = analyze_agent(agent)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(findings, f, indent=2)
    print(f"\nSaved → {OUTPUT_FILE}")

    print_summary(findings)


if __name__ == "__main__":
    main()
