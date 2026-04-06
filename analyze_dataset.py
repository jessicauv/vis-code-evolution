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
COL_COMMENTS       = "comments_count"
COL_FILES          = "files"
COL_BASE_REPO      = "base_repository"
REPO_STARS_KEY     = "stargazerCount"   # key inside the base_repository dict

OUTPUT_FILE = "findings.json"
# ──────────────────────────────────────────────────────────────────────────────


def parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def get_extensions(files_list: list) -> list[str]:
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


def analyze_agent(agent_name: str) -> dict:
    config = f"PullRequests_{agent_name}"
    print(f"  Loading {config} …", flush=True)
    ds = load_dataset(DATASET_NAME, config, split="train", streaming=True)

    pr_sizes: list[float]    = []
    merge_times: list[float] = []
    churn_ratios: list[float]= []
    comments_list: list[float] = []
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

        repo  = row.get(COL_BASE_REPO) or {}
        stars = repo.get(REPO_STARS_KEY, 1) if isinstance(repo, dict) else 1
        if (stars or 0) == 0:
            zero_star += 1

        if (row.get(COL_CLOSING_ISSUES) or 0) > 0:
            issue_linked += 1

        if add > 0:
            churn_ratios.append(dlt / add)

        comments_list.append(row.get(COL_COMMENTS) or 0)

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
        "median_comments":            round(statistics.median(comments_list), 2)  if comments_list  else 0,
    }


def main() -> None:
    findings: dict = {}
    for agent in AGENTS:
        key = AGENT_KEY_MAP[agent]
        print(f"\n[{agent}]")
        findings[key] = analyze_agent(agent)
        stats = findings[key]
        print(
            f"  total={stats['total_prs']:,}  "
            f"merge_rate={stats['merge_rate']:.1%}  "
            f"median_size={stats['median_pr_size']:.0f}  "
            f"top_types={stats['top_file_types']}"
        )

    with open(OUTPUT_FILE, "w") as f:
        json.dump(findings, f, indent=2)
    print(f"\nSaved → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
