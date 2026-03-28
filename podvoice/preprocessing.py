from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pydub import AudioSegment
from pydub.effects import normalize as pydub_normalize
from pydub.silence import detect_nonsilent

from .utils import PodvoiceError


class AudioPreprocessError(PodvoiceError):
    pass


@dataclass(frozen=True)
class PreprocessOptions:
    target_sample_rate: int = 22050
    mono: bool = True
    normalize: bool = True
    trim_silence: bool = True
    min_silence_len_ms: int = 250
    silence_padding_ms: int = 100
    silence_thresh_db_offset: float = 16.0


def preprocess_audio(
    input_path: Path,
    output_path: Path,
    *,
    opts: Optional[PreprocessOptions] = None,
) -> Path:
    """Preprocess a reference audio file for more stable XTTS speaker conditioning.

    This function is intentionally simple and uses pydub/ffmpeg for decoding.

    Returns the written output path.
    """

    opts = opts or PreprocessOptions()
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        audio = AudioSegment.from_file(input_path)
    except Exception as exc:
        raise AudioPreprocessError(f"Failed to decode audio '{input_path}': {exc}") from exc

    if opts.mono:
        audio = audio.set_channels(1)

    if opts.target_sample_rate:
        audio = audio.set_frame_rate(opts.target_sample_rate)

    if opts.trim_silence:
        try:
            silence_thresh = audio.dBFS - opts.silence_thresh_db_offset
            ranges = detect_nonsilent(
                audio,
                min_silence_len=opts.min_silence_len_ms,
                silence_thresh=silence_thresh,
            )
            if ranges:
                start_ms = max(0, ranges[0][0] - opts.silence_padding_ms)
                end_ms = min(len(audio), ranges[-1][1] + opts.silence_padding_ms)
                audio = audio[start_ms:end_ms]
        except Exception:
            # Trimming is best-effort; continue with untrimmed audio.
            pass

    if opts.normalize:
        try:
            audio = pydub_normalize(audio)
        except Exception:
            pass

    try:
        audio.export(output_path, format="wav")
    except Exception as exc:
        raise AudioPreprocessError(f"Failed to export WAV '{output_path}': {exc}") from exc

    return output_path


def concat_reference_audios(
    a: Path,
    b: Path,
    out_path: Path,
    *,
    gap_ms: int = 250,
    target_sample_rate: int = 22050,
) -> Path:
    """Concatenate two reference audios into a single WAV file (mono, resampled)."""

    try:
        a_seg = AudioSegment.from_file(a).set_channels(1).set_frame_rate(target_sample_rate)
        b_seg = AudioSegment.from_file(b).set_channels(1).set_frame_rate(target_sample_rate)
        gap = AudioSegment.silent(duration=gap_ms)
        combined = a_seg + gap + b_seg
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        combined.export(out_path, format="wav")
        return out_path
    except Exception as exc:
        raise AudioPreprocessError(f"Failed to concatenate reference audios: {exc}") from exc


def concat_many_reference_audios(
    paths: list[Path],
    out_path: Path,
    *,
    gap_ms: int = 250,
    target_sample_rate: int = 22050,
) -> Path:
    """Concatenate multiple reference audios into a single WAV file.

    This is useful when a speaker profile contains multiple short clips.
    """

    if not paths:
        raise AudioPreprocessError("No reference audio paths provided.")

    try:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        gap = AudioSegment.silent(duration=gap_ms)
        combined: AudioSegment | None = None
        for p in paths:
            seg = (
                AudioSegment.from_file(p)
                .set_channels(1)
                .set_frame_rate(target_sample_rate)
            )
            combined = seg if combined is None else combined + gap + seg

        assert combined is not None
        combined.export(out_path, format="wav")
        return out_path
    except Exception as exc:
        raise AudioPreprocessError(
            f"Failed to concatenate reference audios: {exc}"
        ) from exc
