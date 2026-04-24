"""In-memory upload-job tracker.

One lock guards concurrent uploads so we never truncate + load twice at once.
State does not survive container restarts — fine for a school demo; any job
still in ``processing`` after a restart is effectively lost and the client
should restart the upload.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

JobStatus = Literal["processing", "succeeded", "failed"]
JobStage = Literal["queued", "unzipping", "loading", "retraining", "done"]


@dataclass
class UploadJob:
    id: str
    status: JobStatus = "processing"
    stage: JobStage = "queued"
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    finished_at: datetime | None = None
    counts: dict[str, int] | None = None
    dropped_transactions: int = 0
    retrain: dict[str, str] = field(default_factory=dict)
    error: str | None = None

    def to_public(self) -> dict:
        return {
            "job_id": self.id,
            "status": self.status,
            "stage": self.stage,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "counts": self.counts,
            "dropped_transactions": self.dropped_transactions,
            "retrain": self.retrain,
            "error": self.error,
        }


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, UploadJob] = {}
        self._lock = threading.Lock()
        # Prevents concurrent uploads from racing on truncate + load.
        self.run_lock = threading.Lock()

    def create(self) -> UploadJob:
        job = UploadJob(id=uuid.uuid4().hex)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> UploadJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[UploadJob]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.started_at, reverse=True)


_store: JobStore | None = None


def get_store() -> JobStore:
    global _store
    if _store is None:
        _store = JobStore()
    return _store
