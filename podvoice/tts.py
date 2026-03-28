"""XTTS v2 loading and inference for podvoice.

This module wraps Coqui's XTTS v2 model behind a small, CPU-friendly
interface suitable for CLI use.
"""

from __future__ import annotations

from pathlib import Path
import inspect
from typing import Dict, Optional

import torch
from TTS.api import TTS as CoquiTTS

from .utils import ModelLoadError, SynthesisError, Segment, stable_hash


class XTTSVoiceEngine:
    """Thin wrapper around Coqui XTTS v2.

    The model is loaded once per process and re-used for all segments.
    Speaker names in the Markdown script are deterministically mapped to
    one of the available Coqui speakers, if any are exposed by the model.
    This gives each logical speaker a consistent voice without requiring
    any custom training or reference audio.
    """

    def __init__(
        self,
        *,
        language: str = "en",
        device: str = "cpu",
        model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2",
        progress_bar: bool = False,
    ) -> None:
        self.language = language
        self.device = device
        self.model_name = model_name

        # Default to CPU for portability; users can explicitly request CUDA.
        if device is None:
            device = "cpu"
        self.device = device

        try:
            # The TTS API accepts the model name positionally.
            tts = CoquiTTS(model_name).to(device)
            # Ensure progress bar configuration is applied if supported.
            try:
                tts.progress_bar = progress_bar
            except AttributeError:
                # Older versions may not expose this attribute; ignore.
                pass
            self._tts = tts
        except Exception as exc:  # pragma: no cover - defensive
            raise ModelLoadError(
                f"Failed to load XTTS model '{model_name}' on device '{device}': {exc}"
            ) from exc

        try:
            sig = inspect.signature(self._tts.tts_to_file)
            self._tts_to_file_params = set(sig.parameters.keys())
        except Exception:  # pragma: no cover - defensive
            self._tts_to_file_params = set()

        # Many multi-speaker models expose a list of built-in speakers.
        # If this list is missing or empty, we simply let XTTS choose its
        # default voice for all segments.
        speakers = getattr(self._tts, "speakers", None) or []
        self._available_speakers = list(speakers)

        # Cache mapping from script speaker name -> internal XTTS speaker id.
        self._speaker_map: Dict[str, Optional[str]] = {}

    @property
    def available_speakers(self) -> list[str]:
        return list(self._available_speakers)

    # ------------------------------------------------------------------
    # Speaker mapping
    # ------------------------------------------------------------------
    def _map_script_speaker(self, script_speaker: str) -> Optional[str]:
        """Map a script speaker name to a concrete XTTS speaker identifier.

        The mapping is deterministic: the same script speaker name always
        maps to the same XTTS speaker as long as the underlying list of
        available speakers does not change.
        """

        if script_speaker in self._speaker_map:
            return self._speaker_map[script_speaker]

        if not self._available_speakers:
            # No explicit speakers; let XTTS use its own default.
            self._speaker_map[script_speaker] = None
            return None

        idx = stable_hash(script_speaker) % len(self._available_speakers)
        chosen = self._available_speakers[idx]
        self._speaker_map[script_speaker] = chosen
        return chosen

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------
    def synthesize_to_path(
        self,
        segment: Segment,
        out_path: Path,
        *,
        builtin_speaker: Optional[str] = None,
        reference_audio: Optional[Path] = None,
        use_default_voice: bool = False,
    ) -> None:
        """Synthesize a single ``Segment`` to a WAV file at ``out_path``.

        The output format is always WAV, which is convenient for further
        processing with pydub.
        """

        out_path = out_path.with_suffix(".wav")

        if use_default_voice:
            speaker_id = None
        else:
            speaker_id = (
                builtin_speaker
                if builtin_speaker
                else self._map_script_speaker(segment.speaker)
            )

        # Prepare keyword arguments for ``tts_to_file``. We only pass
        # parameters that are documented in the Coqui XTTS examples.
        kwargs = {
            "text": segment.text,
            "file_path": str(out_path),
        }

        # Only XTTS-style models expect a language parameter.
        # Many single-language multi-speaker models error if 'language' is provided.
        if "xtts" in (self.model_name or "").lower():
            if not self._tts_to_file_params or "language" in self._tts_to_file_params:
                kwargs["language"] = self.language

        if reference_audio is not None:
            kwargs["speaker_wav"] = str(Path(reference_audio))

        try:
            if speaker_id is not None:
                # Use a built-in Coqui speaker when available.
                self._tts.tts_to_file(speaker=speaker_id, **kwargs)
            else:
                # Fall back to the model's default voice.
                self._tts.tts_to_file(**kwargs)
        except TypeError as exc:
            # Some models (non-multilingual) may not accept 'language'. Retry without it.
            if "language" in kwargs and ("language" in str(exc) or "unexpected" in str(exc)):
                kwargs2 = dict(kwargs)
                kwargs2.pop("language", None)
                try:
                    if speaker_id is not None:
                        self._tts.tts_to_file(speaker=speaker_id, **kwargs2)
                    else:
                        self._tts.tts_to_file(**kwargs2)
                    return
                except Exception:
                    pass
            if reference_audio is not None and "speaker_wav" in str(exc):
                raise SynthesisError(
                    "This coqui-tts version does not support reference-audio cloning (speaker_wav). "
                    "Please upgrade coqui-tts or remove reference_audio from the profile."
                ) from exc
            raise SynthesisError(
                f"Failed to synthesize segment for speaker '{segment.speaker}': {exc}"
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive
            # Some models accept 'language' but will error at runtime when it is set.
            msg = str(exc)
            if "language" in kwargs and "not multi" in msg.lower() and "language" in msg.lower():
                kwargs2 = dict(kwargs)
                kwargs2.pop("language", None)
                try:
                    if speaker_id is not None:
                        self._tts.tts_to_file(speaker=speaker_id, **kwargs2)
                    else:
                        self._tts.tts_to_file(**kwargs2)
                    return
                except Exception:
                    pass
            raise SynthesisError(
                f"Failed to synthesize segment for speaker '{segment.speaker}': {exc}"
            ) from exc
