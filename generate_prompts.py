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
    "merge_rate":                (0.60, 0.90),
    "median_merge_time_minutes": (0,    40),
    "pct_zero_star_repos":       (0.5,  0.8),
    "issue_linking_rate":        (0.0,  0.55),
    "churn_ratio":               (0, 0.4),
}

# File extension → specialty bucket
FILE_TYPE_MAP: dict[str, set[str]] = {
    "frontend": {".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss", ".vue", ".svelte"},
    "backend":  {".py", ".go", ".java", ".rb", ".rs", ".cs", ".php", ".kt", ".scala"},
    "devops":   {".yml", ".yaml", ".dockerfile", ".tf", ".toml", ".sh"},
    "docs":     {".md", ".rst", ".txt", ".adoc"},
}
# ──────────────────────────────────────────────────────────────────────────────

# ─── DESCRIPTION LADDERS ──────────────────────────────────────────────────────
# Each ladder has 5 rungs ordered from lowest to highest intensity.
# pick() maps a 0–1 score onto the appropriate rung.

# 1. PR Size → Scope  (higher score = bigger head)
PR_SIZE_LADDER = [
    "compact refined facial features, perfectly proportioned head",
    "slightly wider-than-normal forehead, gently broadened jaw",
    "noticeably prominent forehead, moderately exaggerated head proportions",
    "large bulging forehead, heavy exaggerated jaw, oversized head",
    "massive oversized bulging forehead, enormous exaggerated jaw, "
    "giga-brain overengineered head proportions",
]

# 2. Merge Rate → Success Rate  (higher score = healthier, more confident)
MERGE_RATE_LADDER = [
    "visible facial bruises, dented crooked nose, battle-worn expression, "
    "dejected sad eyes, rejection energy",
    "faint scuff marks on skin, slightly downturned mouth, weary look",
    "neutral composed expression, slightly uneven skin tone, "
    "hint of cautious optimism",
    "clear healthy skin, symmetrical features, calm confident expression",
    "glowing luminous skin, perfectly symmetrical face, "
    "confident smirk, radiant approved-chad energy",
]

# 3. Merge Time → Speed  (higher score = faster = sharper; lower score = slower = more aged)
#    NOTE: score is inverted before use — slow merge time → high raw value → low speed score
MERGE_SPEED_LADDER = [
    "deep forehead wrinkles, heavy sagging skin, exhausted drooping eyes, "
    "thick beard stubble, aged-by-the-process appearance",
    "noticeable crow's feet, slightly sunken eyes, faint beard shadow, tired look",
    "faint crow's feet around the eyes, slightly tired but alert expression",
    "clean sharp facial features, alert bright eyes, fresh appearance",
    "razor-sharp crisp facial features, bright energetic eyes, "
    "subtle speed-lines at the edges of the body",
]

# 4. Zero-Star Repos → Prestige  (higher score = more zero-star = less prestigious)
#    NOTE: score is inverted — high pct_zero_star → low prestige score
PRESTIGE_LADDER = [
    "drab worn-out clothing, muted desaturated colors, "
    "dim flat lighting, underground indie aesthetic",
    "plain casual clothes, modest neutral lighting, low-key unassuming look",
    "smart-casual business attire, neutral even lighting, "
    "mid-tier professional aesthetic",
    "polished business suit, warm flattering lighting, quietly distinguished air",
    "golden warm halo glow, immaculate luxury suit, "
    "dramatic spotlight from above, celebrity developer energy",
]

# 5. Issue Linking → Organization  (higher score = more organised)
ORGANIZATION_LADDER = [
    "wild chaotic hair flying in all directions, unfocused darting eyes, "
    "faint chaotic scribble marks floating around the head",
    "slightly dishevelled hair, distracted gaze, loosely held crumpled note",
    "loosely styled hair, relaxed posture, casually holding a sticky note",
    "neatly styled hair, attentive focused eyes, small notepad in hand",
    "neat wire-frame glasses, precisely combed hair, "
    "clipboard tucked under arm, organized structured demeanor",
]

# 6. Churn Ratio → Stability  (higher score = more churn = less stable)
#    NOTE: score is inverted — high churn → low stability score
STABILITY_LADDER = [
    "patchwork skin with prominent stitched seams, deep Frankenstein-like scars "
    "across cheeks, constantly-rewriting-himself appearance",
    "several shallow scars and visible skin patches, noticeably uneven texture",
    "skin with a few minor blemishes and shallow scuff marks, "
    "slightly uneven but mostly intact surface",
    "smooth even skin with only the faintest of marks",
    "perfectly smooth marble-like flawless skin texture",
]

# ──────────────────────────────────────────────────────────────────────────────

BASE_PROMPT = (
    "Hyper-realistic full-body portrait of Handsome Squidward on a pure white background. "
    "Photorealistic cartoon style. Head-to-toe visible. Slightly uncanny and exaggerated. "
    "Character is standing upright, facing slightly toward the viewer. "
    "Professional studio lighting. Ultra-detailed. "
)


def normalise(value: float, stat_key: str) -> float:
    """Map a raw stat value to a 0.0–1.0 score using the configured range."""
    lo, hi = STAT_RANGES[stat_key]
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def pick(score: float, ladder: list[str]) -> str:
    """Select the ladder rung that best matches a 0.0–1.0 score."""
    idx = round(score * (len(ladder) - 1))
    return ladder[idx]


def classify_file_specialty(top_file_types: list[str]) -> str:
    counts = {cat: 0 for cat in FILE_TYPE_MAP}
    for ext in top_file_types:
        for cat, exts in FILE_TYPE_MAP.items():
            if ext in exts:
                counts[cat] += 1
    if not any(counts.values()):
        return "backend"
    return max(counts, key=counts.get)


def build_trait_fragments(stats: dict) -> list[str]:
    """Return a list of visual trait strings derived from agent statistics."""
    traits: list[str] = []

    # 1. PR Size → Scope (forehead / head proportions)
    #    High value = bigger PR = more extreme head
    traits.append(pick(
        normalise(stats["median_pr_size"], "median_pr_size"),
        PR_SIZE_LADDER,
    ))

    # 2. Merge Rate → Success Rate (skin quality / expression)
    #    High value = more merges = healthier look
    traits.append(pick(
        normalise(stats["merge_rate"], "merge_rate"),
        MERGE_RATE_LADDER,
    ))

    # 3. Merge Time → Speed (age / sharpness)
    #    High raw value = slow = aged; invert so high speed → high rung
    traits.append(pick(
        1.0 - normalise(stats["median_merge_time_minutes"], "median_merge_time_minutes"),
        MERGE_SPEED_LADDER,
    ))

    # 4. Zero-Star Repos → Prestige (clothing / lighting)
    #    High raw value = more obscure repos = less prestigious; invert
    traits.append(pick(
        1.0 - normalise(stats["pct_zero_star_repos"], "pct_zero_star_repos"),
        PRESTIGE_LADDER,
    ))

    # 5. Issue Linking → Organization (hair / accessories)
    #    High value = more linking = more organised
    traits.append(pick(
        normalise(stats["issue_linking_rate"], "issue_linking_rate"),
        ORGANIZATION_LADDER,
    ))

    # 6. Churn Ratio → Stability (skin texture)
    #    High raw value = more churn = less stable; invert
    traits.append(pick(
        1.0 - normalise(stats["churn_ratio"], "churn_ratio"),
        STABILITY_LADDER,
    ))

    # 7. File Types → Specialty (outfit / accessories)
    #    Categorical — always produces exactly one description
    specialty = classify_file_specialty(stats["top_file_types"])
    specialty_traits = {
        "frontend": (
            "flashy neon-accented streetwear outfit, stylish swooping hair, "
            "vibrant colorful palette"
        ),
        "backend": (
            "formal dark suit and tie, serious composed expression, "
            "conservative muted color palette"
        ),
        "devops": (
            "subtle mechanical cyborg implants on forearms and neck, "
            "metallic sheen on skin patches, small gear-shaped accessories"
        ),
        "docs": (
            "round scholar glasses, holding a thick open book, "
            "tweed academic jacket, warm amber library lighting"
        ),
    }
    traits.append(specialty_traits[specialty])

    return traits


def build_prompt(agent_key: str, stats: dict) -> str:
    traits = build_trait_fragments(stats)
    trait_str = ". ".join(traits) + "." if traits else ""
    label = agent_key.replace("_", " ").title()
    return (
        f"{BASE_PROMPT}"
        f"{trait_str} "
        f"This character embodies the coding personality of: {label}."
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
