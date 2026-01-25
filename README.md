# Podvoice

Local-first, open-source CLI that turns simple Markdown scripts into
multi-speaker audio using Coqui XTTS v2.

Podvoice is designed for developers who want a practical way to turn
podcast-style scripts or conversational content into audio, without
cloud services or paid APIs.

---

## Why this tool exists

- Many TTS tools are tied to proprietary cloud APIs.
- Podcast creators and developers often just want a simple, script-based
  workflow.
- Running everything locally gives you full control over data,
  reproducibility, and cost.

Podvoice aims to be a small, honest, hackable starting point: no
research complexity, no training code, just a clear command line tool
built on stable open-source components.

---

## Features

- **Markdown-based scripts**
  Write your content as a `.md` file with clear speaker blocks.

- **Multiple logical speakers**
  Each speaker name is mapped consistently to a voice in the XTTS model.

- **Single output file**
  Podvoice generates one stitched audio file for the whole script.

- **WAV or MP3 export**
  WAV by default, MP3 when the output path ends with `.mp3`.

- **Local-only inference**
  Uses the pre-trained Coqui XTTS v2 model, downloaded once and cached.

- **CPU-friendly by default**
  Runs on CPU out of the box; GPU is optional if available.

- **Beginner-friendly code**
  Small, modular Python 3.10+ codebase with comments and clear structure.

---

## Input format

Podvoice expects a Markdown file with blocks like this:

```markdown
[SpeakerA | calm]
Hello and welcome to the show.

[SpeakerB | excited]
Aaj hum AI ke baare mein baat karenge.
```

Rules:

- **Speaker name is required**.
- **Emotion is optional** and can be any free-form tag.
- Text continues until the next `[Speaker | emotion]` block.
- Blank lines are allowed inside a block.

In v0.1, the `emotion` tag is parsed and preserved but not interpreted by
XTTS directly. You can still use it for your own tooling or future
extensions.

---

## Quick start

### 1. Prerequisites

- Python **3.10+**
- `ffmpeg` installed on your system (required by `pydub`)
- A stable internet connection **only for the first run**, so that the
  pre-trained XTTS v2 model can be downloaded and cached locally.
- Enough disk space for the model weights (several GB is recommended).

On Ubuntu/Debian, you can typically install ffmpeg with:

```bash
sudo apt-get install ffmpeg
```

### 2. Install dependencies

From the project root:

```bash
pip install -r requirements.txt
```

This will install:

- PyTorch + torchaudio
- Coqui TTS (including XTTS v2)
- pydub
- Typer + Rich
- The `podvoice` package itself (editable install)

### 3. Run the demo

From the project root:

```bash
podvoice render examples/demo.md --out demo.wav
```

or to export MP3:

```bash
podvoice render examples/demo.md --out demo.mp3
```

On first run, Coqui TTS will download the XTTS v2 model and cache it in
your local environment. Subsequent runs reuse the cached model.

---

## CLI usage

The main command is:

```bash
podvoice render SCRIPT.md --out OUTPUT
```

Basic example:

```bash
podvoice render examples/demo.md --out output.wav
```

With explicit options:

```bash
podvoice render \
  examples/demo.md \
  --out podcast.mp3 \
  --language en \
  --device cpu
```

Options:

- **`SCRIPT`** (positional)
  Path to the input Markdown file.

- **`--out` / `-o`**
  Output audio path. If omitted, Podvoice defaults to `SCRIPT` with a
  `.wav` extension.

- **`--language` / `-l`**
  Language code for XTTS v2 (for example `en`, `de`, `fr`). Default is
  `en`.

- **`--device` / `-d`**
  Torch device to run on. Default is `cpu`. If you have a compatible
  GPU, you can try `cuda`.

If anything goes wrong (file not found, invalid Markdown format, model
load issue, or synthesis error), the CLI prints a clear error message
and exits with a non-zero status code.

---

## How voices are assigned

Podvoice does **not** train or fine-tune new voices. Instead, it:

- Uses the pre-trained Coqui XTTS v2 model.
- Queries the list of built-in speakers exposed by the model (if
  available).
- Maps each `speaker` name from your Markdown script to one of these
  built-in speakers using a deterministic hash.

This means:

- Each logical speaker name (like `Host`, `Guest`, `Narrator`) gets a
  consistent voice for the whole script.
- Changing the speaker name (for example, `Alice` vs `Bob`) can change
  which built-in voice is used.
- If the underlying XTTS speaker list changes between versions, the
  mapping may also change.

If the model does not expose named speakers, Podvoice falls back to the
model's default voice for all segments.

---

## Hardware requirements

This project is intentionally conservative so it can run on typical
developer machines.

- **CPU-only by default**
  No GPU is required. The CLI passes `--device cpu` unless you override
  it.

- **Memory**
  8 GB of RAM is a comfortable minimum. More will help when running
  larger scripts.

- **Disk space**
  Expect several gigabytes of disk usage for the XTTS v2 model weights
  and cache.

- **Runtime**
  On CPU, generating longer podcasts can take a while. You can monitor
  progress via the Rich progress bar in the terminal.

---

## Example Markdown script

Here is the example provided in `examples/demo.md`:

```markdown
[Host | calm]
Hello and welcome to the Podvoice demo.

In this short example, we will generate a tiny podcast-style conversation
from a Markdown script.

[Guest | excited]
Aaj hum AI ke baare mein baat karenge.
Yeh saara audio aapke local machine par generate ho raha hai.

[Host | calm]
Thanks for listening. Happy hacking!
```

You can copy this file and adapt it to your own podcast episodes or
conversational content.

---

## Project structure

```text
podvoice/
├── podvoice/
│   ├── __init__.py
│   ├── cli.py         # Typer CLI entrypoint
│   ├── parser.py      # Markdown script parser
│   ├── tts.py         # XTTS loading + inference
│   ├── audio.py       # Audio concatenation/export
│   └── utils.py       # Shared helpers
│
├── examples/
│   └── demo.md        # Sample Markdown script
│
├── requirements.txt
├── pyproject.toml
└── README.md
```

Each module is small and documented so you can easily read and modify it
for your own needs.

---

## Responsible use

Podvoice uses a powerful pre-trained TTS model that can generate natural
sounding speech. Please use it responsibly:

- Do **not** use generated voices to impersonate real people without
  their clear, informed consent.
- Do **not** use this tool for harassment, fraud, or misleading
  activities.
- Make it clear to listeners when content has been generated or
  synthesized.

You are responsible for how you use the tool and for complying with the
licenses of all dependencies, including the Coqui XTTS v2 model.

---

## Contributing

This is an early, practical v0.1. Bug reports, small improvements, and
clear documentation fixes are especially welcome.

Feel free to:

- Open issues with script examples that fail to parse.
- Suggest better defaults for audio normalization or silence between
  segments.
- Improve error messages and CLI UX.

The goal is to keep Podvoice simple, understandable, and genuinely
useful for local-first workflows.
