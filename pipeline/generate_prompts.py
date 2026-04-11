"""
Step 2: Translate findings.json statistics into DALL-E 3 image prompts.

Re-runnable: reads findings.json, overwrites prompts.json.

Usage:
    python generate_prompts.py
"""

import json

# ─── CONFIG ───────────────────────────────────────────────────────────────────
INPUT_FILE  = "findings.json"
OUTPUT_FILE = "prompts.json"

# Expected real-world (min, max) range for each numeric stat across all agents.
# Values outside the range are clamped to [0, 1] during normalisation.
STAT_RANGES = {
    "median_pr_size":            (50,   400),
    "median_merge_time_minutes": (0,    40),
    "merge_rate":                (0.60, 0.90),
}

# ──────────────────────────────────────────────────────────────────────────────

# ─── DESCRIPTION LADDERS ──────────────────────────────────────────────────────
# Each ladder has 5 rungs ordered from lowest to highest intensity.
# pick() maps a 0–1 score onto the appropriate rung.

# 1. PR Size → Scope  (higher score = bigger head)
PR_SIZE_LADDER = [
    "compact refined facial features, perfectly proportioned head",
    "slightly wider-than-normal forehead",
    "noticeably prominent forehead, moderately exaggerated head proportions",
    "large bulging forehead, oversized head",
    "massive oversized bulging forehead, "
    "giga-brain overengineered head proportions",
]

# 2. Merge Time → Speed
# (aerodynamic/slicked hair for fast, wild/unkempt for slow)
# NOTE: score is inverted before use — slow merge time → high raw value → low speed score
MERGE_SPEED_LADDER = [
    "wild tangled overgrown hair, chaotic strands jutting in all directions, completely untamed",
    "loosely disheveled hair, several strands out of place, unkempt and unmanaged",
    "neatly combed hair, tidy and well-maintained, no particular style",
    "sharply side-parted hair, cleanly styled with precise lines, polished appearance",
    "aerodynamically slicked-back hair, perfectly streamlined as if caught in a wind tunnel, every strand in place",
]

# 3. Merge Rate → Success Rate  (higher score = healthier, more confident)
MERGE_RATE_LADDER = [
    "visible facial bruises, dented crooked nose, battle-worn expression, "
    "dejected sad eyes, rejection energy",
    "faint scuff marks on skin, slightly downturned mouth, weary look",
    "neutral composed expression, variation in skin tone",
    "clear healthy skin, symmetrical features, calm confident expression",
    "glowing luminous skin, perfectly symmetrical face, "
    "confident smirk, radiant approved-chad energy",
]
# ──────────────────────────────────────────────────────────────────────────────

BASE_PROMPT = (
    "Cartoon realism close-up portrait, neck-up framing, full face visible, centered on a pure white background. "
    "Clearly non-photorealistic, stylized cartoon character, not a real human. "
    "Professional studio lighting with soft shadows and high detail. "
)


def normalise(value: float, stat_key: str) -> float:
    """Map a raw stat value to a 0.0–1.0 score using the configured range."""
    lo, hi = STAT_RANGES[stat_key]
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def pick(score: float, ladder: list[str]) -> str:
    """Select the ladder rung that best matches a 0.0–1.0 score."""
    idx = round(score * (len(ladder) - 1))
    return ladder[idx]


def build_trait_fragments(stats: dict) -> list[str]:
    """Return a list of visual trait strings derived from agent statistics."""
    traits: list[str] = []

    # 1. PR Size → Scope (forehead / head proportions)
    #    High value = bigger PR = more extreme head
    traits.append(pick(
        normalise(stats["median_pr_size"], "median_pr_size"),
        PR_SIZE_LADDER,
    ))

    # 2. Merge Time → Speed (hair style)
    #    High raw value = slow = disheveled; invert so high speed → high rung
    traits.append(pick(
        1.0 - normalise(stats["median_merge_time_minutes"], "median_merge_time_minutes"),
        MERGE_SPEED_LADDER,
    ))

    # 3. Merge Rate → Approval (eye expression / confidence)
    #    High value = more merges = higher rung (no inversion needed)
    traits.append(pick(
        normalise(stats["merge_rate"], "merge_rate"),
        MERGE_RATE_LADDER,
    ))

    return traits


def build_prompt(agent_key: str, stats: dict) -> str:
    traits = build_trait_fragments(stats)
    trait_str = ". ".join(traits) + "." if traits else ""
    label = agent_key.replace("_", " ").title()
    return (
        f"{BASE_PROMPT}"
        f"{trait_str} "
    )


def main() -> None:
    with open(INPUT_FILE) as f:
        findings: dict = json.load(f)

    prompts: dict = {}
    for agent_key, stats in findings.items():
        prompt = build_prompt(agent_key, stats)
        prompts[agent_key] = prompt
        print(f"[{agent_key}]\n  {prompt[:140]}…\n")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(prompts, f, indent=2)
    print(f"Saved → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
