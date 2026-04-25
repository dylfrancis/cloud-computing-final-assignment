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
import json
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
        kwargs: dict = {"lookback_days": LOOKBACK_DAYS}
        # Basket: the default min_support=0.02 expects a product pair to appear
        # in 2% of baskets, which is too high for the 84.51° sample (~250k
        # baskets) and yields an empty associations frame. 0.001 (0.1%) gives
        # us enough pair candidates that active households still have
        # non-overlapping recommendations after the "already-purchased" filter
        # in predict — at 0.005 the few pairs that survived were all popular
        # products everyone had already bought.
        if name == "basket":
            kwargs["min_support"] = 0.001
        metrics = await model.train(session, **kwargs)
    save_model(name, model)
    print(f"[{name}] done in {time.perf_counter() - started:.1f}s -> {artifact_path(name)}")
    print(f"[{name}] metrics:")
    print(json.dumps(metrics, indent=2, default=str))

    # For churn, also dump class balance + the predict_proba distribution
    # across every household so we can see whether the model produces real
    # variance or saturates. Only do this when we have a single trained model
    # in memory (i.e. we just trained churn) to avoid extra DB load.
    if name == "churn":
        await _diagnose_churn(model)


async def _diagnose_churn(model: ChurnModel) -> None:
    """Print class balance and probability distribution for churn."""
    import numpy as np

    from app.ml.feature_engineering import get_churn_features, prepare_training_data

    async with SessionLocal() as session:
        features_df = await get_churn_features(session, lookback_days=LOOKBACK_DAYS)
        if features_df.empty:
            print("[churn] diagnose: no features")
            return
        feature_frame = (
            features_df[model.feature_names] if model.feature_names else features_df
        )
        X, _ = prepare_training_data(feature_frame)
        probs = model.predict_proba(X)[:, 1] if hasattr(model, "predict_proba") else (
            model.model.predict_proba(X)[:, 1]
        )
    qs = np.percentile(probs, [0, 10, 25, 50, 75, 90, 100])
    print(
        f"[churn] proba distribution across {len(probs)} households: "
        f"min={qs[0]:.3f} p10={qs[1]:.3f} p25={qs[2]:.3f} median={qs[3]:.3f} "
        f"p75={qs[4]:.3f} p90={qs[5]:.3f} max={qs[6]:.3f}"
    )
    bands = {
        "<0.10": int((probs < 0.10).sum()),
        "0.10-0.30": int(((probs >= 0.10) & (probs < 0.30)).sum()),
        "0.30-0.50": int(((probs >= 0.30) & (probs < 0.50)).sum()),
        "0.50-0.70": int(((probs >= 0.50) & (probs < 0.70)).sum()),
        ">=0.70": int((probs >= 0.70).sum()),
    }
    print(f"[churn] proba bands: {bands}")

    # Pull example household IDs per band so you can copy/paste them into
    # the dashboard and verify the model produces variety.
    hshd_nums = features_df.index.to_numpy()
    band_specs = [
        ("<0.10", probs < 0.10),
        ("0.10-0.30", (probs >= 0.10) & (probs < 0.30)),
        ("0.30-0.50", (probs >= 0.30) & (probs < 0.50)),
        ("0.50-0.70", (probs >= 0.50) & (probs < 0.70)),
        (">=0.70", probs >= 0.70),
    ]
    for label, mask in band_specs:
        idxs = np.where(mask)[0][:5]
        examples = [(int(hshd_nums[i]), float(probs[i])) for i in idxs]
        if examples:
            pretty = ", ".join(f"#{h}={p:.2f}" for h, p in examples)
            print(f"[churn] {label} examples: {pretty}")


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
