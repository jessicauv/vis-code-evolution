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
from datetime import datetime
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

# Column names in the Repositories_{agent} table (used for star count lookup)
REPO_CONFIG_TEMPLATE = "Repositories_{agent}"
COL_REPO_PR_ID       = "pr_id"        # joins to COL_PR_ID in PullRequests
COL_REPO_STARS       = "stargazer_count"

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


def build_stars_lookup(agent_name: str) -> Dict[str, int]:
    """Stream Repositories_{agent} and return {pr_id: stargazer_count}."""
    config = REPO_CONFIG_TEMPLATE.format(agent=agent_name)
    print(f"  Loading {config} for star counts …", flush=True)
    ds = load_dataset(DATASET_NAME, config, split="train", streaming=True)
    return {
        row[COL_REPO_PR_ID]: (row.get(COL_REPO_STARS) or 0)
        for row in ds
    }


def analyze_agent(agent_name: str) -> Dict:
    stars_lookup = build_stars_lookup(agent_name)

    config = f"PullRequests_{agent_name}"
    print(f"  Loading {config} …", flush=True)
    ds = load_dataset(DATASET_NAME, config, split="train", streaming=True)

    pr_sizes: List[float]     = []
    merge_times: List[float]  = []
    churn_ratios: List[float] = []
    merges    = 0
    total     = 0
    zero_star = 0
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

        stars = stars_lookup.get(row.get(COL_PR_ID), 1)  # default 1 = not zero-star
        if stars == 0:
            zero_star += 1

        if (row.get(COL_CLOSING_ISSUES) or 0) > 0:
            issue_linked += 1

        if add > 0:
            churn_ratios.append(dlt / add)

        for ext in get_extensions(row.get(COL_FILES) or []):
            ext_counter[ext] += 1

        if total % 50_000 == 0:
            print(f"    … {total:,} rows processed", flush=True)

    top_file_types = [ext for ext, _ in ext_counter.most_common(5)]

    return {
        "total_prs":                  total,
        "median_pr_size":             round(statistics.median(pr_sizes), 2)       if pr_sizes       else 0,
        "merge_rate":                 round(merges / total, 4)                    if total          else 0,
        "median_merge_time_minutes":  round(statistics.median(merge_times), 2)    if merge_times    else 0,
        "pct_zero_star_repos":        round(zero_star / total, 4)                 if total          else 0,
        "issue_linking_rate":         round(issue_linked / total, 4)              if total          else 0,
        "churn_ratio":                round(statistics.median(churn_ratios), 4)   if churn_ratios   else 0,
        "top_file_types":             top_file_types,
    }


def print_summary(findings: Dict) -> None:
    STAT_LABELS = [
        ("total_prs",                 "Total PRs",            "{:>10,.0f}"),
        ("median_pr_size",            "Median PR Size (lines)","{:>10.1f}"),
        ("merge_rate",                "Merge Rate",            "{:>10.1%}"),
        ("median_merge_time_minutes", "Merge Time (min)",      "{:>10.1f}"),
        ("pct_zero_star_repos",       "Zero-Star Repos %",     "{:>10.1%}"),
        ("issue_linking_rate",        "Issue Linking Rate",    "{:>10.1%}"),
        ("churn_ratio",               "Churn Ratio",           "{:>10.4f}"),
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
