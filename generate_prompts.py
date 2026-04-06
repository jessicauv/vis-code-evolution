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

# Thresholds that map numeric stats to visual traits.
# Adjust these to tune character appearances.
THRESHOLDS = {
    "pr_size": {
        "large": 500,       # total lines changed → big PR
        "small": 100,
    },
    "merge_rate": {
        "high": 0.75,
        "low":  0.40,
    },
    "merge_time_minutes": {
        "fast": 60 * 24,        # ≤ 1 day
        "slow": 60 * 24 * 7,   # ≥ 1 week
    },
    "pct_zero_star": {
        "high": 0.60,   # mostly obscure repos
        "low":  0.20,   # mostly popular repos
    },
    "issue_linking": {
        "high": 0.40,
        "low":  0.10,
    },
    "churn": {
        "high": 0.80,   # heavy rewriting
        "low":  0.20,
    },
    "comments": {
        "high": 3.0,
        "low":  1.0,
    },
}

# File extension → specialty bucket
FILE_TYPE_MAP: dict[str, set[str]] = {
    "frontend": {".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss", ".vue", ".svelte"},
    "backend":  {".py", ".go", ".java", ".rb", ".rs", ".cs", ".php", ".kt", ".scala"},
    "devops":   {".yml", ".yaml", ".dockerfile", ".tf", ".toml", ".sh"},
    "docs":     {".md", ".rst", ".txt", ".adoc"},
}
# ──────────────────────────────────────────────────────────────────────────────

BASE_PROMPT = (
    "Hyper-realistic full-body portrait of Handsome Squidward on a pure white background. "
    "Photorealistic cartoon style. Head-to-toe visible. Slightly uncanny and exaggerated. "
    "Character is standing upright, facing slightly toward the viewer. "
    "Professional studio lighting. Ultra-detailed. "
)


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
    t = THRESHOLDS
    traits: list[str] = []

    # 1. PR Size → Scope (forehead / head proportions)
    size = stats["median_pr_size"]
    if size >= t["pr_size"]["large"]:
        traits.append(
            "oversized bulging forehead, exaggerated massive jaw, "
            "giga-brain overengineered head proportions"
        )
    elif size <= t["pr_size"]["small"]:
        traits.append("compact refined facial features, perfectly proportioned head")
    else:
        traits.append("slightly prominent forehead, mildly exaggerated head proportions")

    # 2. Merge Rate → Success Rate (skin quality / expression)
    rate = stats["merge_rate"]
    if rate >= t["merge_rate"]["high"]:
        traits.append(
            "glowing healthy luminous skin, perfectly symmetrical face, "
            "confident subtle smirk, radiant approved-chad energy"
        )
    elif rate <= t["merge_rate"]["low"]:
        traits.append(
            "visible facial bruises, dented crooked nose, battle-worn expression, "
            "dejected sad eyes, rejection energy"
        )
    else:
        traits.append(
            "neutral composed expression, slightly uneven skin tone, "
            "hint of cautious optimism"
        )

    # 3. Merge Time → Speed (age / sharpness)
    mtime = stats["median_merge_time_minutes"]
    if mtime <= t["merge_time_minutes"]["fast"]:
        traits.append(
            "sharp crisp facial features, subtle speed-lines at the edges of the body"
        )
    elif mtime >= t["merge_time_minutes"]["slow"]:
        traits.append(
            "deep forehead wrinkles, heavy sagging skin, exhausted drooping eyes, "
            "sparse beard stubble, aged-by-the-process appearance"
        )
    else:
        traits.append(
            "faint crow's feet around the eyes, slightly tired but alert expression"
        )

    # 4. Zero-Star Repos → Prestige (clothing / lighting)
    pct_zero = stats["pct_zero_star_repos"]
    if pct_zero >= t["pct_zero_star"]["high"]:
        traits.append(
            "drab worn-out clothing, muted desaturated colors, "
            "dim flat lighting, indie underground aesthetic"
        )
    elif pct_zero <= t["pct_zero_star"]["low"]:
        traits.append(
            "golden warm halo glow, immaculate luxury suit, "
            "dramatic spotlight from above, celebrity developer energy"
        )
    else:
        traits.append(
            "smart-casual business attire, neutral even lighting, "
            "mid-tier professional aesthetic"
        )

    # 5. Issue Linking → Organization (hair / accessories)
    linking = stats["issue_linking_rate"]
    if linking >= t["issue_linking"]["high"]:
        traits.append(
            "neat wire-frame glasses, precisely combed hair, "
            "clipboard tucked under arm, organized structured demeanor"
        )
    elif linking <= t["issue_linking"]["low"]:
        traits.append(
            "wild chaotic hair flying in all directions, unfocused darting eyes, "
            "faint chaotic scribble marks floating around the head"
        )
    else:
        traits.append(
            "loosely styled hair, relaxed posture, casually holding a sticky note"
        )

    # 6. Churn Ratio → Stability (skin texture)
    churn = stats["churn_ratio"]
    if churn >= t["churn"]["high"]:
        traits.append(
            "patchwork skin with visible stitched seams, Frankenstein-like scars "
            "across cheeks, constantly-rewriting-himself appearance"
        )
    elif churn <= t["churn"]["low"]:
        traits.append("perfectly smooth marble-like flawless skin texture")
    else:
        traits.append(
            "skin with a few minor blemishes and shallow scuff marks, "
            "slightly uneven but mostly intact surface"
        )

    # 7. File Types → Specialty (outfit / accessories)
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

    # 8. Developer Interaction → Sociability (background / expression)
    comments = stats["median_comments"]
    if comments >= t["comments"]["high"]:
        traits.append(
            "highly expressive animated face, admiring silhouetted figures "
            "visible in the background, small speech bubbles floating nearby"
        )
    elif comments <= t["comments"]["low"]:
        traits.append(
            "blank stoic stare, completely empty white background, "
            "lone-wolf isolated atmosphere"
        )

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
