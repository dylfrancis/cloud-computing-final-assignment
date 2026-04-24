"""Persist / restore trained models across container restarts.

Azure App Service Linux mounts ``/home`` from a persistent Azure File Share,
so artifacts written there survive deploys and restarts. Falls back to a
repo-local directory when ``/home`` isn't writable (local dev).

Pickle is version-sensitive — a scikit-learn/pandas bump in
``requirements.txt`` can make old artifacts unloadable. Load errors are
caught and logged rather than fatal, so the app always boots even if the
saved model is incompatible; callers just see the model as untrained and
can retrain.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TypeVar

import joblib

log = logging.getLogger(__name__)

T = TypeVar("T")


def _artifact_dir() -> Path:
    """Resolve the writable artifact directory — `/home/ml-artifacts` in
    Azure App Service, or `backend/app/ml/artifacts/` locally."""
    primary = Path("/home/ml-artifacts")
    try:
        primary.mkdir(parents=True, exist_ok=True)
        probe = primary / ".write_probe"
        probe.write_text("")
        probe.unlink()
        return primary
    except OSError:
        fallback = Path(__file__).resolve().parent / "artifacts"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def artifact_path(name: str) -> Path:
    return _artifact_dir() / f"{name}.joblib"


def save_model(name: str, obj: object) -> None:
    path = artifact_path(name)
    try:
        joblib.dump(obj, path, compress=3)
        log.info("persisted %s model -> %s", name, path)
    except Exception as exc:  # noqa: BLE001
        log.warning("failed to persist %s model: %s", name, exc)


def load_model(name: str, expected_type: type[T]) -> T | None:
    path = artifact_path(name)
    if not path.exists():
        return None
    try:
        obj = joblib.load(path)
    except Exception as exc:  # noqa: BLE001
        log.warning("failed to load %s model from %s: %s", name, path, exc)
        return None
    if not isinstance(obj, expected_type):
        log.warning(
            "ignoring %s artifact at %s: expected %s, got %s",
            name,
            path,
            expected_type.__name__,
            type(obj).__name__,
        )
        return None
    return obj
