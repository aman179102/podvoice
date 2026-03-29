---

# 🧠 **Podvoice**

Local-first, open-source CLI that turns simple Markdown scripts into
**multi-speaker audio** using **Coqui XTTS v2**.

Podvoice is built for developers who want a **boring, reliable, offline**
text-to-speech workflow — no cloud APIs, no subscriptions, no vendor lock-in.

Runs on **Linux, Windows, macOS, and FreeBSD**.

---

## Why Podvoice exists

* Most modern TTS tools depend on proprietary cloud services
* Developers want reproducible, script-based workflows
* Podcasts and narration should not require paid APIs

Podvoice is intentionally:

* Small
* Honest
* Hackable
* Local-first

No training pipelines.
No research code.
Just a clean CLI built on stable open-source components.

---

## Features

* **Markdown-based scripts**
* **Multiple logical speakers**
* **Deterministic voice assignment**
* **Single stitched output file**
* **WAV or MP3 export**
* **Local-only inference**
* **CPU-first (GPU optional)**
* **Cross-platform support**
* **🎙️ Studio Web UI** — Modern single-page interface for voice selection, preview, and generation
* **🔊 Built-in multi-speaker models** — VCTK vits and others with cached voice demos
* **⚡ AJAX-based generation** — No page reloads, instant audio playback
* **🎨 Modern dark theme** — Clean sidebar layout with zero scrolling
* **📁 Profile management** — YAML-based speaker profiles with reference audio support
* **🔄 Multi-reference audio** — Concatenate multiple clips for better voice conditioning

---

## Supported platforms

| Platform | Status            | Notes                  |
| -------- | ----------------- | ---------------------- |
| Linux    | ✅ Fully supported | Primary dev platform   |
| macOS    | ✅ Fully supported | Intel + Apple Silicon  |
| Windows  | ✅ Fully supported | PowerShell             |
| FreeBSD  | ✅ Supported       | Requires ffmpeg        |
| WSL2     | ✅ Supported       | Recommended on Windows |

---

## Input format

Podvoice consumes Markdown files with speaker blocks:

```markdown
[Host | calm]
Welcome to the show.

[Guest | warm]
If this sounds useful, try writing your own script
and see how easily Markdown becomes audio.
```

Rules:

* Speaker name is **required**
* Emotion tag is **optional**
* Text continues until the next speaker block
* Blank lines are allowed


---

## ▶️ Demo Video

<div align="center">
  


https://github.com/user-attachments/assets/c9e9c5f0-ce03-4d71-952f-927cab55bd83



</div>

## 🎧 Demo Audio

<div align="center">
  


https://github.com/user-attachments/assets/6f468a4f-c4c9-446c-a6b9-b365c3e7f131






</div>

---

## Quick start (ALL operating systems)

### 1️⃣ System requirements (common)

Required everywhere:

* **Python 3.10.x**
* **ffmpeg**
* **espeak** or **espeak-ng** (required for Studio with built-in multi-speaker models)
* Internet access **only for first run**
* ~5–8 GB free disk space (model cache)

---

### 2️⃣ Install system dependencies

#### 🐧 Linux (Ubuntu / Debian)

```bash
sudo apt update
sudo apt install -y python3.10 python3.10-venv ffmpeg git espeak
```

---

#### 🍎 macOS (Homebrew)

```bash
brew install python@3.10 ffmpeg git
```

---

#### 🪟 Windows (PowerShell)

```powershell
winget install Python.Python.3.10
winget install ffmpeg
winget install Git.Git
```

Restart the terminal after installing Python.

---

#### 🐡 FreeBSD

```sh
pkg install python310 ffmpeg git
```

---

### 3️⃣ Clone the repository

```bash
git clone https://github.com/aman179102/podvoice.git
cd podvoice
```

---

## Setup (recommended path)

### 🐧 Linux / 🍎 macOS / 🐡 FreeBSD

```bash
chmod +x bootstrap.sh
./bootstrap.sh
```

This script will:

* Verify Python 3.10
* Create a local `.venv`
* Install fully pinned dependencies from `requirements.lock`
* Install `podvoice` in editable mode

---

### 🪟 Windows (PowerShell)

#### One-time: allow local scripts

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

#### Run bootstrap

```powershell
.\bootstrap.ps1
```

---

### Activate the environment

#### Linux / macOS / FreeBSD

```bash
source .venv/bin/activate
```

#### Windows

```powershell
.venv\Scripts\Activate.ps1
```

---

## Run the demo

```bash
podvoice examples/demo.md --out demo.wav
```

Or export MP3:

```bash
podvoice examples/demo.md --out demo.mp3
```

On first run, Coqui XTTS v2 model weights will be downloaded and cached locally.
Subsequent runs reuse the cache.

---

## 🎙️ Studio Web UI

Podvoice includes a modern, single-page web interface for interactive voice generation.

### Launch Studio

```bash
podvoice studio --host 127.0.0.1 --port 8000
```

Then open: `http://127.0.0.1:8000`

### Studio Features

| Feature | Description |
|---------|-------------|
| **Sidebar Voice Gallery** | All built-in speakers displayed with human-friendly labels |
| **Instant Preview** | Click any voice to hear a demo instantly (cached after first play) |
| **Single TTS** | Type text, select voice, generate audio — no page reloads |
| **Multi TTS (Podcast)** | Paste Markdown scripts with speaker mapping |
| **AJAX Generation** | Audio generates and plays without leaving the page |
| **Modern Dark Theme** | Clean aesthetic with CSS variables, no scrolling |

### Studio Endpoints

- `/` or `/single` — Single TTS page
- `/multi` — Multi-speaker podcast page
- `/demo_wav?voice=p240` — Get cached demo audio for a voice
- `/health` — Health check endpoint

### Using a Different Model

Studio defaults to `tts_models/en/vctk/vits` (built-in multi-speaker). To use XTTS v2 instead:

```bash
podvoice studio --model-name tts_models/multilingual/multi-dataset/xtts_v2
```

---

## CLI usage

```bash
podvoice SCRIPT.md --out OUTPUT
```

Examples:

```bash
podvoice examples/demo.md --out output.wav
```

```bash
podvoice examples/demo.md --out podcast.mp3 --language en --device cpu
```

### Options

| Option             | Description               |
| ------------------ | ------------------------- |
| `SCRIPT`           | Input Markdown file       |
| `--out`, `-o`      | Output `.wav` or `.mp3`   |
| `--language`, `-l` | XTTS language code        |
| `--device`, `-d`   | `cpu` (default) or `cuda` |

---

## GPU usage (optional)

If you have a compatible NVIDIA GPU:

```bash
podvoice examples/demo.md --device cuda
```

If CUDA is unavailable, Podvoice safely falls back to CPU.

---

## 📁 Profile Management

Podvoice supports YAML-based speaker profiles for advanced use cases.

### Profile Directory

Default: `./podvoice_profiles/profiles.yaml`

### Profile Format

```yaml
profiles:
  my_custom_voice:
    builtin_speaker: p240
  cloned_voice:
    reference_audio: ./samples/voice.wav
  multi_sample_voice:
    reference_audios:
      - ./samples/clip1.wav
      - ./samples/clip2.wav
      - ./samples/clip3.wav
```

### Using Profiles

Profiles are automatically loaded and can be referenced in your Markdown scripts by speaker name.

---

## Performance notes

You may see warnings like:

```
Could not initialize NNPACK! Reason: Unsupported hardware.
```

✔️ These are **harmless**
✔️ Audio generation will still complete
❌ No action required

---

## How voices are assigned

Podvoice does **not** train voices.

Instead:

* Uses built-in XTTS v2 speakers
* Hashes speaker names deterministically
* Maps each logical speaker to a stable voice

Implications:

* Same speaker name → same voice
* Rename speaker → possibly different voice
* XTTS update → mapping may change

Fallback: default XTTS voice.

---

## Project structure

```text
podvoice/
├── podvoice/
│   ├── cli.py            # CLI entrypoint
│   ├── parser.py         # Markdown parser
│   ├── tts.py            # XTTS inference
│   ├── audio.py          # Audio stitching
│   ├── studio.py         # FastAPI web UI
│   ├── profiles.py       # YAML profile management
│   ├── preprocessing.py  # Audio preprocessing
│   └── utils.py
│
├── examples/
│   └── demo.md
│
├── podvoice_profiles/    # Voice profiles directory
│
├── bootstrap.sh
├── bootstrap.ps1
├── pyproject.toml
└── README.md
```

---

## Responsible use

Podvoice generates natural-sounding speech.

Do **not**:

* Impersonate real people without consent
* Use generated audio for fraud or deception

Always disclose synthesized content where appropriate.

You are responsible for compliance with all applicable laws and licenses,
including those of Coqui XTTS v2.

---

## Contributing

Podvoice is intentionally simple.

Good contributions:

* Bug reports with minimal reproduction scripts
* CLI UX improvements
* Documentation clarity
* Cross-platform fixes

Non-goals:

* Cloud dependencies
* Training pipelines
* Over-engineering

**Goal:** local, boring, reliable software.

