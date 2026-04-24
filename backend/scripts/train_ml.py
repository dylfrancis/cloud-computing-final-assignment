"""Train the three ML models locally against the configured DATABASE_URL and
persist joblibs to ``backend/app/ml/artifacts/``.

Usage:
    python -m scripts.train_ml                 # train all three
    python -m scripts.train_ml clv             # just one
    python -m scripts.train_ml clv churn       # any subset

Then push to prod: ``python -m scripts.push_ml``.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

from app.config import get_settings  # noqa: F401 — validates .env
from app.db import SessionLocal
from app.ml.basket_model import BasketModel
from app.ml.churn_model import ChurnModel
from app.ml.clv_model import CLVModel
from app.ml.persistence import artifact_path, save_model

MODELS = {"clv": CLVModel, "churn": ChurnModel, "basket": BasketModel}

# Matches the server-side default in app/ml/trainer.py so local runs mirror
# what the prod retrain would do.
LOOKBACK_DAYS = 365 * 20


async def train(name: str) -> None:
    cls = MODELS[name]
    print(f"[{name}] training...")
    started = time.perf_counter()
    model = cls()
    async with SessionLocal() as session:
        await model.train(session, lookback_days=LOOKBACK_DAYS)
    save_model(name, model)
    print(f"[{name}] done in {time.perf_counter() - started:.1f}s -> {artifact_path(name)}")


async def main(names: list[str]) -> int:
    for name in names:
        await train(name)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models", nargs="*", default=[], help="Subset to train; default = all")
    args = parser.parse_args()

    names = args.models or list(MODELS)
    bad = [n for n in names if n not in MODELS]
    if bad:
        print(f"Unknown model(s): {bad}. Valid: {list(MODELS)}", file=sys.stderr)
        sys.exit(2)

    sys.exit(asyncio.run(main(names)))
