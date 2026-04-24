"""Upload new Households / Products / Transactions CSVs and retrain ML models.

Accepts either:
- A single ``.zip`` containing the three CSVs (course-provided format), or
- Three individual CSVs via ``households``, ``products``, ``transactions`` form
  fields. Each field is optional; if only some are provided, only those tables
  are touched. (Zip uploads always replace all three.)

Each request enqueues a background job that:
  1. Extracts + validates the CSVs,
  2. Truncates + bulk-inserts the affected tables,
  3. Re-trains the three ML models against the new data.

Responses return a ``job_id``; poll ``GET /uploads/{job_id}`` for progress.
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import get_settings, sync_database_url
from app.data_load import (
    bulk_insert,
    load_households,
    load_products,
    load_transactions,
)
from app.db import SessionLocal
from app.deps import get_current_user_email
from app.ml.registry import get_registry
from app.models.household import Household
from app.models.product import Product
from app.models.transaction import Transaction
from app.schemas.upload import UploadJobResponse, UploadListResponse
from app.uploads.job_store import JobStore, UploadJob, get_store

router = APIRouter(
    prefix="/uploads",
    tags=["uploads"],
    dependencies=[Depends(get_current_user_email)],
)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

_HOUSEHOLD_KEYWORDS = ("household",)
_PRODUCT_KEYWORDS = ("product",)
_TRANSACTION_KEYWORDS = ("transaction",)


def _find_csv(paths: Iterable[Path], keywords: Iterable[str]) -> Path | None:
    for p in paths:
        name = p.name.lower()
        if name.endswith(".csv") and any(k in name for k in keywords):
            return p
    return None


async def _save_upload(file: UploadFile, dst: Path) -> None:
    written = 0
    with dst.open("wb") as fh:
        while chunk := await file.read(1024 * 1024):
            written += len(chunk)
            if written > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
                )
            fh.write(chunk)


def _unzip_into(zip_path: Path, dest: Path) -> list[Path]:
    extracted: list[Path] = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = Path(info.filename).name
            if not name.lower().endswith(".csv"):
                continue
            target = dest / name
            with zf.open(info) as src, target.open("wb") as out:
                shutil.copyfileobj(src, out)
            extracted.append(target)
    return extracted


def _load_sync(
    store: JobStore,
    job: UploadJob,
    hh_path: Path | None,
    pr_path: Path | None,
    tx_path: Path | None,
) -> None:
    """Sync DB load using pyodbc fast_executemany. Called inside a thread."""
    url = sync_database_url(get_settings().database_url)
    engine = create_engine(url, fast_executemany=True)

    with store.run_lock, Session(engine) as session:
        job.stage = "loading"

        households = load_households(hh_path) if hh_path else []
        products = load_products(pr_path) if pr_path else []

        transactions: list[dict] = []
        dropped = 0
        if tx_path:
            valid_hshds = (
                {h["hshd_num"] for h in households}
                if hh_path
                else {row[0] for row in session.query(Household.hshd_num).all()}
            )
            valid_products = (
                {p["product_num"] for p in products}
                if pr_path
                else {row[0] for row in session.query(Product.product_num).all()}
            )
            transactions, dropped = load_transactions(tx_path, valid_hshds, valid_products)

        # Any replacement of a parent table requires wiping the child table
        # first — transactions FK into both products and households.
        must_clear_transactions = bool(tx_path or pr_path or hh_path)
        if must_clear_transactions:
            session.query(Transaction).delete()
            session.commit()
        if pr_path:
            session.query(Product).delete()
            session.commit()
        if hh_path:
            session.query(Household).delete()
            session.commit()

        if households:
            bulk_insert(session, Household, households)
        if products:
            bulk_insert(session, Product, products)
        if transactions:
            bulk_insert(session, Transaction, transactions)

    job.counts = {
        "households": len(households),
        "products": len(products),
        "transactions": len(transactions),
    }
    job.dropped_transactions = dropped


async def _retrain(job: UploadJob) -> None:
    job.stage = "retraining"
    registry = get_registry()
    # Seed all three up-front as pending so clients see the full checklist
    # immediately, then flip each to running/ok/failed as it progresses.
    job.retrain = {"clv": "pending", "churn": "pending", "basket": "pending"}
    async with SessionLocal() as session:
        for name, model in (
            ("clv", registry.get_clv()),
            ("churn", registry.get_churn()),
            ("basket", registry.get_basket()),
        ):
            job.retrain = {**job.retrain, name: "running"}
            try:
                await model.train(session)
                job.retrain = {**job.retrain, name: "ok"}
            except Exception as exc:
                job.retrain = {**job.retrain, name: f"failed: {exc}"}


async def _process_job(
    store: JobStore,
    job: UploadJob,
    workdir: Path,
    hh_path: Path | None,
    pr_path: Path | None,
    tx_path: Path | None,
) -> None:
    try:
        await asyncio.to_thread(_load_sync, store, job, hh_path, pr_path, tx_path)
        await _retrain(job)
        job.status = "succeeded"
        job.stage = "done"
    except HTTPException as exc:
        job.status = "failed"
        job.error = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    except Exception as exc:
        job.status = "failed"
        job.error = f"{type(exc).__name__}: {exc}"
    finally:
        job.finished_at = datetime.now(tz=timezone.utc)
        shutil.rmtree(workdir, ignore_errors=True)


@router.post("", response_model=UploadJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_upload(
    background: BackgroundTasks,
    archive: UploadFile | None = File(default=None),
    households: UploadFile | None = File(default=None),
    products: UploadFile | None = File(default=None),
    transactions: UploadFile | None = File(default=None),
    store: JobStore = Depends(get_store),
) -> UploadJobResponse:
    if not any([archive, households, products, transactions]):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Provide either 'archive' (zip) or one or more of "
            "'households', 'products', 'transactions' CSVs.",
        )

    job = store.create()
    workdir = Path(tempfile.mkdtemp(prefix=f"upload-{job.id}-"))

    hh_path: Path | None = None
    pr_path: Path | None = None
    tx_path: Path | None = None

    try:
        if archive is not None:
            job.stage = "unzipping"
            zip_path = workdir / (archive.filename or "upload.zip")
            await _save_upload(archive, zip_path)
            extracted = _unzip_into(zip_path, workdir)
            zip_path.unlink(missing_ok=True)
            hh_path = _find_csv(extracted, _HOUSEHOLD_KEYWORDS)
            pr_path = _find_csv(extracted, _PRODUCT_KEYWORDS)
            tx_path = _find_csv(extracted, _TRANSACTION_KEYWORDS)
            if not (hh_path and pr_path and tx_path):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Archive must contain household, product, and transaction CSVs.",
                )
        else:
            if households is not None:
                hh_path = workdir / "households.csv"
                await _save_upload(households, hh_path)
            if products is not None:
                pr_path = workdir / "products.csv"
                await _save_upload(products, pr_path)
            if transactions is not None:
                tx_path = workdir / "transactions.csv"
                await _save_upload(transactions, tx_path)
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise

    background.add_task(_process_job, store, job, workdir, hh_path, pr_path, tx_path)
    return UploadJobResponse(**job.to_public())


@router.get("", response_model=UploadListResponse)
async def list_uploads(store: JobStore = Depends(get_store)) -> UploadListResponse:
    return UploadListResponse(jobs=[UploadJobResponse(**j.to_public()) for j in store.list()])


@router.get("/{job_id}", response_model=UploadJobResponse)
async def get_upload(job_id: str, store: JobStore = Depends(get_store)) -> UploadJobResponse:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Upload job {job_id} not found")
    return UploadJobResponse(**job.to_public())
