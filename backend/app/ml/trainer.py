"""Shared ML retrain orchestration.

One module-level async lock and status dict that both the upload background
task and the ``POST /ml/retrain`` endpoint share. This way the dashboard can
auto-kick training and poll ``/ml/status`` for live per-model progress without
two different code paths.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Literal, TypedDict

from app.db import SessionLocal
from app.ml.persistence import save_model
from app.ml.registry import get_registry

ModelName = Literal["clv", "churn", "basket"]
ModelStatus = Literal["pending", "running", "ok", "failed"]


class ModelState(TypedDict):
    status: ModelStatus
    trained: bool
    training_date: str | None
    error: str | None


_lock = asyncio.Lock()
_task: asyncio.Task | None = None
_state: dict[ModelName, ModelState] = {
    "clv": {"status": "pending", "trained": False, "training_date": None, "error": None},
    "churn": {"status": "pending", "trained": False, "training_date": None, "error": None},
    "basket": {"status": "pending", "trained": False, "training_date": None, "error": None},
}


def _snapshot_trained() -> None:
    """Sync the 'trained' flag from the registry on each read in case something
    else (e.g. teammate's per-model endpoint) trained a model directly."""
    reg = get_registry()
    _state["clv"]["trained"] = bool(reg.get_clv().is_trained)
    _state["clv"]["training_date"] = (
        reg.get_clv().training_date.isoformat() if reg.get_clv().training_date else None
    )
    _state["churn"]["trained"] = bool(reg.get_churn().is_trained)
    _state["churn"]["training_date"] = (
        reg.get_churn().training_date.isoformat() if reg.get_churn().training_date else None
    )
    _state["basket"]["trained"] = reg.get_basket().associations is not None


def get_status() -> dict:
    _snapshot_trained()
    running = any(s["status"] == "running" for s in _state.values())
    return {"is_training": running, "models": _state}


# The 84.51° sample is from 2018–2020. Models default to a 365-day lookback
# which excludes every row once the demo runs any time in 2021+. Override
# with a generous 20-year window so we always pick up the full dataset.
_DEFAULT_LOOKBACK_DAYS = 365 * 20


async def _train_one(name: ModelName) -> None:
    reg = get_registry()
    model = {"clv": reg.get_clv(), "churn": reg.get_churn(), "basket": reg.get_basket()}[name]
    _state[name]["status"] = "running"
    _state[name]["error"] = None
    try:
        async with SessionLocal() as session:
            await model.train(session, lookback_days=_DEFAULT_LOOKBACK_DAYS)
        _state[name]["status"] = "ok"
        _state[name]["trained"] = True
        # clv/churn set training_date internally; basket only has .associations.
        date = getattr(model, "training_date", None) or datetime.now(tz=timezone.utc)
        _state[name]["training_date"] = date.isoformat()
        # Persist to /home so restarts don't lose the trained model.
        save_model(name, model)
    except Exception as exc:
        _state[name]["status"] = "failed"
        _state[name]["error"] = f"{type(exc).__name__}: {exc}"


async def _train_all() -> None:
    try:
        # Reset to "pending" for any models not currently trained; keep
        # trained ones so users see the prior state until they flip to running.
        for name in ("clv", "churn", "basket"):
            if _state[name]["status"] not in ("ok",):
                _state[name]["status"] = "pending"
        for name in ("clv", "churn", "basket"):
            await _train_one(name)  # type: ignore[arg-type]
    finally:
        global _task
        _task = None


def kick_off_retrain() -> dict:
    """Start a retrain task if one isn't already running. Idempotent."""
    global _task
    if _task is None or _task.done():
        loop = asyncio.get_running_loop()
        _task = loop.create_task(_train_all())
    return get_status()


def is_training() -> bool:
    return _task is not None and not _task.done()
