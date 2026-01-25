"""Markdown script parser for podvoice.

The expected format is a sequence of speaker blocks, e.g.::

    [Alice | calm]
    Hello and welcome to the show.

    [Bob | excited]
    Aaj hum AI ke baare mein baat karenge.

Speaker name is required, emotion is optional. Text for a block continues
until the next ``[Speaker | emotion]`` header. Blank lines are allowed.
"""

from __future__ import annotations

import re
from typing import List

from .utils import Segment, ScriptParseError


# Matches lines such as "[Alice]" or "[Bob | excited]".
_HEADER_RE = re.compile(
    r"^\[(?P<speaker>[^\]|]+)(?:\s*\|\s*(?P<emotion>[^\]]+))?\]\s*$"
)


def parse_markdown_script(text: str, source: str = "<string>") -> List[Segment]:
    """Parse a Markdown script into an ordered list of ``Segment`` objects.

    Parameters
    ----------
    text:
        The raw contents of the Markdown file.
    source:
        Human-readable name of the source, used only in error messages.
    """

    lines = text.splitlines()

    segments: List[Segment] = []
    current_speaker: str | None = None
    current_emotion: str | None = None
    current_lines: list[str] = []
    current_header_line: int | None = None

    def flush_current() -> None:
        nonlocal current_speaker, current_emotion, current_lines, current_header_line
        if current_speaker is None:
            return
        content = "\n".join(current_lines).strip()
        if not content:
            raise ScriptParseError(
                f"Speaker block starting at line {current_header_line} in {source} "
                "does not contain any text."
            )
        segments.append(
            Segment(
                speaker=current_speaker,
                emotion=current_emotion,
                text=content,
            )
        )
        current_speaker = None
        current_emotion = None
        current_lines = []
        current_header_line = None

    for lineno, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        header_match = _HEADER_RE.match(stripped)
        if header_match:
            # Starting a new speaker block.
            if current_speaker is not None:
                flush_current()

            speaker = header_match.group("speaker").strip()
            if not speaker:
                raise ScriptParseError(
                    f"Empty speaker name at line {lineno} in {source}."
                )
            emotion = header_match.group("emotion")
            emotion = emotion.strip() if emotion else None

            current_speaker = speaker
            current_emotion = emotion
            current_lines = []
            current_header_line = lineno
            continue

        # Non-header line.
        if current_speaker is None:
            # Ignore leading blank lines that appear before the first header.
            if stripped == "":
                continue
            raise ScriptParseError(
                f"Found text outside a speaker block at line {lineno} in {source}. "
                "Every piece of text must follow a [Speaker | emotion] header."
            )

        current_lines.append(raw_line)

    # Flush the final block.
    if current_speaker is not None:
        flush_current()

    if not segments:
        raise ScriptParseError(f"No speaker blocks were found in script {source}.")

    return segments
