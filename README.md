# Visualizing Code Evolution

## Project Overview
Visualizing Code Evolution is a web app that compares how human developers and AI coding agents write code using real pull request data from over 100,000 PRs (see [MOSAIC-agentic-3m](https://huggingface.co/datasets/AISE-TUDelft/MOSAIC-agentic-3m) HuggingFace dataset). Slide between six authors (Human, Claude Code, GitHub Copilot, Google Jules, Cognition AI Devin, and OpenAI Codex) and see how their coding behaviour differs across metrics like PR size, merge rate, and merge speed. Each author is represented by a generated portrait (inspired by "Handsome Squidward"), whose visual traits map directly to their stats.

The project is meant to open up conversations on accountability, agency, and the emerging relationship between humans and the systems that increasingly co-author our digital world.

<!-- Add GIF -->

## Technical Architecture

**Core Technologies**<br>
Static HTML / CSS / JavaScript website. Python data pipeline (run locally) to generate stats and portraits. Deployed on Vercel.

**Technical Features**
- Streams and analyzes the  (~100k+ PRs) via a Python pipeline
- Stats (see table below) computed per agent and stored in `findings.json`
- AI-generated portraits via DALL-E 3 — visual traits (head proportions, hair style, expression) are derived from the same stats using 5-rung description ladders
- Animated character crossfades and bar chart transitions using GSAP
- Annotation cards on each portrait dynamically compute and display the ladder-derived trait text directly from `findings.json`

| Stat | Description |
|---|---|
| Median PR Size | Lines added + deleted, median across all PRs |
| Merge Rate | Share of PRs that were merged |
| Median Merge Time | Time from PR open to merge |
| Issue Linking Rate | Share of PRs that close at least one issue |
| Top File Types | Most-touched file extensions |

## Usage & Testing
**Using the Deployed Application**

🔗 The app is live & ready to use - <a href="https://vis-code-evolution.vercel.app">Try It Out</a>

### Local Development Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Add your OpenAI API key - optional (only needed if using DALL-E to generate images)
cp .env.example .env
# Edit .env: OPENAI_API_KEY=sk-...

# Run the pipeline (from the pipeline/ directory)
cd pipeline
python analyze_dataset.py    # Step 1: generate findings.json
python generate_prompts.py   # Step 2: generate DALL-E prompts
# Delete existing images in public/images before running Step 3
python generate_images.py    # Step 3 (optional): generate portraits + copy findings.json to public/
                             # If you skip Step 3, generate portraits using your preferred method,
                             # place them in public/images/ with the names below, and manually
                             # copy findings.json to public/findings.json.
# Required image filenames: human.png, claude_code.png, copilot.png, jules.png, devin.png, codex.png

# Serve the site locally (any static file server)
cd ../public
npx serve .
```

## Disclosures

**AI Usage Statement**<br>
This project leverages AI technologies in the following ways:

- AI in the application: DALL-E 3 is used to generate the character portraits based on prompts derived from pull request statistics. No AI runs at runtime — all images are pre-generated.
- AI in development: Used AI-assisted tools such as Claude Code. All AI-generated code was reviewed & tested.
