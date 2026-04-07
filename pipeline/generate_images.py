"""
Step 3: Call DALL-E 3 to generate one image per agent, save to public/images/.

Re-runnable: skips images that already exist so partial runs are safe.
Also copies findings.json → public/findings.json for the website.

Usage:
    python generate_images.py

Required environment variable (put in .env):
    OPENAI_API_KEY=sk-...
"""

import json
import shutil
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ─── CONFIG ───────────────────────────────────────────────────────────────────
PROMPTS_FILE  = "prompts.json"
FINDINGS_FILE = "findings.json"
OUTPUT_DIR    = Path("public/images")

IMAGE_MODEL   = "dall-e-3"
IMAGE_SIZE    = "1024x1792"   # portrait — shows the full body
IMAGE_QUALITY = "hd"
# ──────────────────────────────────────────────────────────────────────────────


def download_image(url: str, dest: Path) -> None:
    urllib.request.urlretrieve(url, dest)


def main() -> None:
    client = OpenAI()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(PROMPTS_FILE) as f:
        prompts: dict = json.load(f)

    for agent_key, prompt in prompts.items():
        out_path = OUTPUT_DIR / f"{agent_key}.png"
        if out_path.exists():
            print(f"[{agent_key}] Skipping — image already exists at {out_path}")
            continue

        print(f"[{agent_key}] Generating image …", flush=True)
        response = client.images.generate(
            model=IMAGE_MODEL,
            prompt=prompt,
            size=IMAGE_SIZE,
            quality=IMAGE_QUALITY,
            n=1,
            response_format="url",
        )
        image_url = response.data[0].url
        download_image(image_url, out_path)
        print(f"[{agent_key}] Saved → {out_path}")

    # Make findings.json available to the website
    dest = Path("public") / "findings.json"
    shutil.copy(FINDINGS_FILE, dest)
    print(f"\nCopied {FINDINGS_FILE} → {dest}")
    print("Done.")


if __name__ == "__main__":
    main()
