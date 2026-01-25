"""Typer-based command line interface for podvoice.

The main entrypoint is ``podvoice render``, which takes a Markdown
script and produces a single audio file.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.traceback import install as install_rich_traceback

from .parser import parse_markdown_script
from .tts import XTTSVoiceEngine
from .audio import build_podcast, export_audio
from .utils import (
    PodvoiceError,
    ScriptParseError,
    ModelLoadError,
    SynthesisError,
)


app = typer.Typer(help="Convert Markdown scripts into multi-speaker audio.")
console = Console()
install_rich_traceback(show_locals=False)


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
                try:
                    engine.synthesize_to_path(segment, out_path)
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


if __name__ == "__main__":  # pragma: no cover
    app()
