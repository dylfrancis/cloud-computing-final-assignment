from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class UploadJobResponse(BaseModel):
    job_id: str
    status: Literal["processing", "succeeded", "failed"]
    stage: Literal["queued", "unzipping", "loading", "retraining", "done"]
    started_at: datetime
    finished_at: datetime | None = None
    counts: dict[str, int] | None = None
    dropped_transactions: int = 0
    retrain: dict[str, str] = {}
    error: str | None = None


class UploadListResponse(BaseModel):
    jobs: list[UploadJobResponse]
