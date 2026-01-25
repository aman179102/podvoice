"""Shared utilities and simple data structures for podvoice.

We keep this module intentionally small and beginner-friendly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import hashlib


class PodvoiceError(Exception):
    """Base exception for all podvoice-specific errors."""


class ScriptParseError(PodvoiceError):
    """Raised when the input Markdown script cannot be parsed."""


class ModelLoadError(PodvoiceError):
    """Raised when the TTS model cannot be loaded."""


class SynthesisError(PodvoiceError):
    """Raised when TTS synthesis fails for a segment."""


@dataclass
class Segment:
    """A single speech segment in the script.

    Attributes
    ----------
    speaker:
        Name of the speaker, as written in the Markdown block.
    emotion:
        Optional emotion tag (e.g. "calm", "excited"). This is not
        interpreted by the TTS model directly in v0.1, but is kept for
        future use and for potential downstream tooling.
    text:
        The spoken content for this segment.
    """

    speaker: str
    emotion: Optional[str]
    text: str


def stable_hash(text: str) -> int:
    """Return a deterministic integer hash for mapping names to speakers.

    Python's built-in ``hash`` is randomized between processes. For
    reproducible behavior, we base our mapping on an MD5 digest instead.
    This is only used for speaker name -> XTTS speaker mapping and does
    not have any security implications.
    """

    digest = hashlib.md5(text.encode("utf-8")).hexdigest()
    return int(digest, 16)
