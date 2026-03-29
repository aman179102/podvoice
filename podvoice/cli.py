"""Typer-based command line interface for podvoice.

The main entrypoint is ``podvoice render``, which takes a Markdown
script and produces a single audio file.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import shutil

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.traceback import install as install_rich_traceback

from .parser import parse_markdown_script
from .tts import XTTSVoiceEngine
from .audio import build_podcast, export_audio
from .profiles import (
    default_profiles_dir,
    init_profiles_file,
    load_profiles,
    profiles_file_path,
    validate_profiles,
)
from .preprocessing import concat_many_reference_audios
from .studio import run_studio
from .utils import (
    PodvoiceError,
    ScriptParseError,
    ModelLoadError,
    SynthesisError,
)


app = typer.Typer(help="Convert Markdown scripts into multi-speaker audio.")
console = Console()
install_rich_traceback(show_locals=False)

profiles_app = typer.Typer(help="Manage voice profiles.")
voices_app = typer.Typer(help="Inspect available voices.")
app.add_typer(profiles_app, name="profiles")
app.add_typer(voices_app, name="voices")


@app.command()
def render(
    script: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the input Markdown script (*.md).",
    ),
    out: Path = typer.Option(
        None,
        "--out",
        "-o",
        help="Output audio file (.wav or .mp3). Defaults to <script-name>.wav",
    ),
    language: str = typer.Option(
        "en",
        "--language",
        "-l",
        help="Language code for XTTS v2 (e.g. en, de, fr).",
    ),
    device: str = typer.Option(
        "cpu",
        "--device",
        "-d",
        help="Torch device to run on (default: 'cpu'). Use 'cuda' if you have a GPU.",
    ),
    profiles_dir: Path = typer.Option(
        None,
        "--profiles-dir",
        help="Directory containing podvoice_profiles/profiles.yaml (default: ./podvoice_profiles).",
    ),
) -> None:
    """Render a Markdown script into a single audio file."""

    console.print(
        Panel.fit(
            "Podvoice v0.1 — Markdown to multi-speaker audio (XTTS v2)",
            style="bold cyan",
        )
    )

    if out is None:
        out = script.with_suffix(".wav")
    elif out.suffix.lower() not in {".wav", ".mp3"}:
        # If the user provided a path without extension, default to WAV.
        if out.suffix == "":
            out = out.with_suffix(".wav")
        else:
            console.print(
                "[red]Error:[/] Output path must end with .wav or .mp3.",
            )
            raise typer.Exit(code=1)

    try:
        raw_text = script.read_text(encoding="utf-8")
    except OSError as exc:
        console.print(f"[red]Failed to read script:[/] {exc}")
        raise typer.Exit(code=1)

    # ------------------------------------------------------------------
    # Parse script
    # ------------------------------------------------------------------
    try:
        segments = parse_markdown_script(raw_text, source=str(script))
    except ScriptParseError as exc:
        console.print(f"[red]Invalid script format:[/] {exc}")
        raise typer.Exit(code=1)

    if not segments:
        console.print("[red]Script did not contain any speaker segments.[/]")
        raise typer.Exit(code=1)

    # ------------------------------------------------------------------
    # Load XTTS model
    # ------------------------------------------------------------------
    console.print(
        f"[bold]Loading XTTS v2 model[/bold] on device '[green]{device}[/green]'…"
    )
    try:
        engine = XTTSVoiceEngine(language=language, device=device)
    except ModelLoadError as exc:
        console.print(f"[red]Model load failed:[/] {exc}")
        raise typer.Exit(code=1)

    if profiles_dir is None:
        profiles_dir = default_profiles_dir()
    profiles_path = profiles_file_path(profiles_dir)
    try:
        profiles = load_profiles(profiles_path)
    except PodvoiceError as exc:
        console.print(f"[red]Failed to load profiles:[/] {exc}")
        raise typer.Exit(code=1)

    # ------------------------------------------------------------------
    # Synthesize segments and stitch audio
    # ------------------------------------------------------------------
    with tempfile.TemporaryDirectory(prefix="podvoice_") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        segment_paths: list[Path] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "Synthesizing speech segments…", total=len(segments)
            )

            for idx, segment in enumerate(segments):
                out_path = tmp_dir / f"segment_{idx:04d}.wav"
                profile = profiles.get(segment.speaker)
                ref = None
                if profile is not None and profile.mode == "reference":
                    refs = profile.reference_audios or (
                        [profile.reference_audio] if profile.reference_audio else []
                    )
                    refs = [p for p in refs if p is not None]
                    if len(refs) == 1:
                        ref = refs[0]
                    elif len(refs) > 1:
                        ref = concat_many_reference_audios(
                            refs, tmp_dir / f"ref_{idx:04d}.wav"
                        )
                try:
                    engine.synthesize_to_path(
                        segment,
                        out_path,
                        builtin_speaker=(profile.builtin_speaker if profile else None),
                        reference_audio=ref,
                    )
                except SynthesisError as exc:
                    console.print(f"[red]Synthesis failed:[/] {exc}")
                    raise typer.Exit(code=1)

                segment_paths.append(out_path)
                progress.update(task, advance=1)

        try:
            combined = build_podcast(segment_paths)
        except PodvoiceError as exc:
            console.print(f"[red]Audio processing failed:[/] {exc}")
            raise typer.Exit(code=1)

        try:
            export_audio(combined, out)
        except PodvoiceError as exc:
            console.print(f"[red]Export failed:[/] {exc}")
            raise typer.Exit(code=1)

    console.print(f"[green]Done.[/] Wrote [bold]{out}[/].")


@profiles_app.command("init")
def profiles_init(
    profiles_dir: Path = typer.Option(
        None,
        "--profiles-dir",
        help="Directory to create ./podvoice_profiles/profiles.yaml in (default: ./podvoice_profiles).",
    ),
) -> None:
    if profiles_dir is None:
        profiles_dir = default_profiles_dir()
    path = profiles_file_path(profiles_dir)
    try:
        init_profiles_file(path)
    except PodvoiceError as exc:
        console.print(f"[red]Failed:[/] {exc}")
        raise typer.Exit(code=1)
    console.print(f"[green]Created[/] {path}")


@profiles_app.command("validate")
def profiles_validate(
    profiles_dir: Path = typer.Option(
        None,
        "--profiles-dir",
        help="Directory containing ./podvoice_profiles/profiles.yaml (default: ./podvoice_profiles).",
    ),
) -> None:
    if profiles_dir is None:
        profiles_dir = default_profiles_dir()
    path = profiles_file_path(profiles_dir)
    try:
        validate_profiles(path)
    except PodvoiceError as exc:
        console.print(f"[red]Invalid:[/] {exc}")
        raise typer.Exit(code=1)
    console.print(f"[green]OK[/] {path}")


@voices_app.command("list")
def voices_list(
    language: str = typer.Option(
        "en",
        "--language",
        "-l",
        help="Language code for XTTS v2 (e.g. en, de, fr).",
    ),
    device: str = typer.Option(
        "cpu",
        "--device",
        "-d",
        help="Torch device to run on (default: 'cpu'). Use 'cuda' if you have a GPU.",
    ),
) -> None:
    try:
        engine = XTTSVoiceEngine(language=language, device=device)
    except ModelLoadError as exc:
        console.print(f"[red]Model load failed:[/] {exc}")
        raise typer.Exit(code=1)

    if not engine.available_speakers:
        console.print("No built-in speakers were exposed by this model.")
        return

    for s in engine.available_speakers:
        console.print(s)


@app.command()
def studio(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
    language: str = typer.Option("en", "--language", "-l"),
    device: str = typer.Option("cpu", "--device", "-d"),
    model_name: str = typer.Option(
        "tts_models/en/vctk/vits",
        "--model-name",
        help="TTS model to use in Studio. Defaults to a built-in multi-speaker model.",
    ),
    profiles_dir: Path = typer.Option(
        None,
        "--profiles-dir",
        help="Directory containing ./podvoice_profiles/profiles.yaml (default: ./podvoice_profiles).",
    ),
) -> None:
    if profiles_dir is None:
        profiles_dir = default_profiles_dir()

    if "vctk" in model_name.lower():
        if shutil.which("espeak-ng") is None and shutil.which("espeak") is None:
            raise PodvoiceError(
                "Studio model requires an espeak backend, but none was found. "
                "Install 'espeak-ng' (preferred) or 'espeak' on your system, or pass a different --model-name."
            )
    run_studio(
        host=host,
        port=port,
        profiles_dir=profiles_dir,
        language=language,
        device=device,
        model_name=model_name,
    )


if __name__ == "__main__":  # pragma: no cover
    app()
