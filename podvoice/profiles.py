from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .utils import PodvoiceError


class ProfileError(PodvoiceError):
    pass


@dataclass(frozen=True)
class SpeakerProfile:
    name: str
    mode: str
    builtin_speaker: Optional[str] = None
    reference_audio: Optional[Path] = None
    reference_audios: Optional[list[Path]] = None


def default_profiles_dir(project_root: Path | None = None) -> Path:
    root = project_root or Path.cwd()
    return root / "podvoice_profiles"


def profiles_file_path(profiles_dir: Path) -> Path:
    return Path(profiles_dir) / "profiles.yaml"


def load_profiles(profiles_path: Path) -> Dict[str, SpeakerProfile]:
    profiles_path = Path(profiles_path)
    if not profiles_path.exists():
        return {}

    try:
        raw = yaml.safe_load(profiles_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ProfileError(f"Failed to read profiles file '{profiles_path}': {exc}") from exc

    if raw is None:
        return {}

    if not isinstance(raw, dict) or "profiles" not in raw:
        raise ProfileError(
            f"Invalid profiles format in '{profiles_path}'. Expected a top-level mapping with key 'profiles'."
        )

    items = raw.get("profiles")
    if not isinstance(items, list):
        raise ProfileError(f"Invalid 'profiles' value in '{profiles_path}'. Expected a list.")

    out: Dict[str, SpeakerProfile] = {}
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ProfileError(
                f"Invalid profile at index {idx} in '{profiles_path}'. Expected a mapping."
            )

        name = str(item.get("name") or "").strip()
        mode = str(item.get("mode") or "").strip()
        if not name:
            raise ProfileError(f"Profile at index {idx} in '{profiles_path}' is missing 'name'.")
        if mode not in {"reference", "builtin"}:
            raise ProfileError(
                f"Profile '{name}' in '{profiles_path}' has invalid mode '{mode}'. Use 'reference' or 'builtin'."
            )

        builtin_speaker = item.get("builtin_speaker")
        if builtin_speaker is not None:
            builtin_speaker = str(builtin_speaker)

        reference_audio_paths: list[Path] = []
        reference_audios = item.get("reference_audios")
        if reference_audios is not None:
            if not isinstance(reference_audios, list):
                raise ProfileError(
                    f"Profile '{name}' in '{profiles_path}' has invalid 'reference_audios'. Expected a list."
                )
            for p in reference_audios:
                reference_audio_paths.append(
                    (profiles_path.parent / str(p)).expanduser().resolve()
                )
        else:
            reference_audio = item.get("reference_audio")
            if reference_audio is not None:
                reference_audio_paths.append(
                    (profiles_path.parent / str(reference_audio)).expanduser().resolve()
                )

        reference_audio_path: Optional[Path] = reference_audio_paths[0] if reference_audio_paths else None

        profile = SpeakerProfile(
            name=name,
            mode=mode,
            builtin_speaker=builtin_speaker,
            reference_audio=reference_audio_path,
            reference_audios=reference_audio_paths or None,
        )

        if profile.mode == "builtin" and not profile.builtin_speaker:
            raise ProfileError(f"Profile '{name}' is mode 'builtin' but missing 'builtin_speaker'.")
        if profile.mode == "reference" and not profile.reference_audio:
            raise ProfileError(
                f"Profile '{name}' is mode 'reference' but missing 'reference_audio' or 'reference_audios'."
            )

        out[name] = profile

    return out


def validate_profiles(profiles_path: Path) -> None:
    profiles = load_profiles(profiles_path)
    for name, profile in profiles.items():
        if profile.mode == "reference":
            paths = profile.reference_audios or ([profile.reference_audio] if profile.reference_audio else [])
            if not paths:
                raise ProfileError(
                    f"Profile '{name}' is mode 'reference' but has no reference audio files."
                )

            for p in paths:
                if p is None:
                    continue
                if not p.exists():
                    raise ProfileError(
                        f"Profile '{name}' reference audio not found: '{p}'."
                    )
                if not p.is_file():
                    raise ProfileError(
                        f"Profile '{name}' reference audio is not a file: '{p}'."
                    )


def init_profiles_file(profiles_path: Path) -> None:
    profiles_path = Path(profiles_path)
    profiles_path.parent.mkdir(parents=True, exist_ok=True)
    if profiles_path.exists():
        raise ProfileError(f"Profiles file already exists: '{profiles_path}'.")

    template: Dict[str, Any] = {
        "profiles": [
            {
                "name": "Host",
                "mode": "reference",
                "reference_audios": ["samples/host.wav"],
            },
            {
                "name": "Guest",
                "mode": "builtin",
                "builtin_speaker": "speaker_0",
            },
        ]
    }

    try:
        profiles_path.write_text(yaml.safe_dump(template, sort_keys=False), encoding="utf-8")
    except Exception as exc:
        raise ProfileError(f"Failed to write profiles file '{profiles_path}': {exc}") from exc
