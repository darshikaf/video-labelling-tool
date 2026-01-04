"""
Job Management System for Async Operations

Provides an abstraction for running long-running tasks (like mask propagation)
in the background, allowing the API to return immediately and clients to poll
for results.

Architecture:
- JobManager: Abstract base class defining the interface
- InMemoryJobManager: Simple in-memory implementation (Phase 1)
- Future: CeleryJobManager for production (Phase 2 - Redis/Celery)

This design allows easy migration from in-memory to persistent job queue
without changing API endpoints or client code.
"""

import logging
import time
import uuid
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import Lock
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    """Represents a background job"""

    job_id: str
    job_type: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0  # 0-100
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)


class JobManager(ABC):
    """
    Abstract base class for job management.

    This interface allows swapping between different backends (in-memory, Redis, Celery)
    without changing the API layer.
    """

    @abstractmethod
    def submit_job(
        self, job_type: str, task_func: Callable, params: Dict[str, Any]
    ) -> str:
        """
        Submit a job for background execution.

        Args:
            job_type: Type of job (e.g., "propagate_masks")
            task_func: Function to execute in background
            params: Parameters to pass to the function

        Returns:
            job_id: Unique identifier for tracking the job
        """
        pass

    @abstractmethod
    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job status and result.

        Args:
            job_id: Job identifier

        Returns:
            Job object with current status, or None if not found
        """
        pass

    @abstractmethod
    def update_progress(self, job_id: str, progress: float) -> None:
        """
        Update job progress (0-100).

        Args:
            job_id: Job identifier
            progress: Progress percentage (0-100)
        """
        pass

    @abstractmethod
    def cleanup_old_jobs(self, max_age_seconds: int = 3600) -> int:
        """
        Remove completed/failed jobs older than max_age_seconds.

        Args:
            max_age_seconds: Maximum age of jobs to keep

        Returns:
            Number of jobs cleaned up
        """
        pass


class InMemoryJobManager(JobManager):
    """
    Simple in-memory job manager using ThreadPoolExecutor.

    Suitable for development and single-server deployments.
    Jobs are lost on server restart.

    For production with multiple workers, migrate to CeleryJobManager.
    """

    def __init__(self, max_workers: int = 2):
        """
        Initialize in-memory job manager.

        Args:
            max_workers: Maximum number of concurrent background jobs
        """
        self.jobs: Dict[str, Job] = {}
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="job-worker"
        )
        self.lock = Lock()
        logger.info(f"InMemoryJobManager initialized with {max_workers} workers")

    def submit_job(
        self, job_type: str, task_func: Callable, params: Dict[str, Any]
    ) -> str:
        """Submit a job for background execution"""
        job_id = str(uuid.uuid4())

        # Create job record
        job = Job(
            job_id=job_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
            params=params,
        )

        with self.lock:
            self.jobs[job_id] = job

        # Submit to executor
        future = self.executor.submit(self._execute_job, job_id, task_func, params)

        # Store future for potential cancellation (optional)
        with self.lock:
            self.jobs[job_id].status = JobStatus.RUNNING
            self.jobs[job_id].started_at = datetime.now()

        logger.info(f"Job {job_id} ({job_type}) submitted for execution")
        return job_id

    def _sanitize_result(self, result: Any) -> Any:
        """
        Sanitize result to remove non-serializable data (like numpy arrays).

        For propagate_masks results, we only keep metadata and remove the
        frames dictionary which contains numpy arrays.
        """
        if isinstance(result, dict):
            # Create a clean copy without frames (contains numpy arrays)
            sanitized = {}
            for key, value in result.items():
                # Skip 'frames' key as it contains numpy arrays
                if key != 'frames':
                    sanitized[key] = value
            return sanitized
        return result

    def _execute_job(
        self, job_id: str, task_func: Callable, params: Dict[str, Any]
    ) -> None:
        """Execute job in background thread"""
        try:
            logger.info(f"Job {job_id} started execution")

            # Execute the task
            result = task_func(**params)

            # Sanitize result to remove non-serializable data
            sanitized_result = self._sanitize_result(result)

            # Mark as completed
            with self.lock:
                if job_id in self.jobs:
                    self.jobs[job_id].status = JobStatus.COMPLETED
                    self.jobs[job_id].completed_at = datetime.now()
                    self.jobs[job_id].progress = 100.0
                    self.jobs[job_id].result = sanitized_result

            logger.info(f"Job {job_id} completed successfully")

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)

            # Mark as failed
            with self.lock:
                if job_id in self.jobs:
                    self.jobs[job_id].status = JobStatus.FAILED
                    self.jobs[job_id].completed_at = datetime.now()
                    self.jobs[job_id].error = str(e)

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job status and result"""
        with self.lock:
            return self.jobs.get(job_id)

    def update_progress(self, job_id: str, progress: float) -> None:
        """Update job progress"""
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].progress = max(0.0, min(100.0, progress))

    def cleanup_old_jobs(self, max_age_seconds: int = 3600) -> int:
        """Remove completed/failed jobs older than max_age_seconds"""
        now = datetime.now()
        count = 0

        with self.lock:
            jobs_to_remove = []
            for job_id, job in self.jobs.items():
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                    if job.completed_at:
                        age = (now - job.completed_at).total_seconds()
                        if age > max_age_seconds:
                            jobs_to_remove.append(job_id)

            for job_id in jobs_to_remove:
                del self.jobs[job_id]
                count += 1

        if count > 0:
            logger.info(f"Cleaned up {count} old jobs")

        return count

    def get_all_jobs(self) -> Dict[str, Job]:
        """Get all jobs (for debugging/monitoring)"""
        with self.lock:
            return self.jobs.copy()

    def shutdown(self) -> None:
        """Shutdown executor gracefully"""
        logger.info("Shutting down InMemoryJobManager")
        self.executor.shutdown(wait=True)


# ============================================================
# Placeholder for Future Phase 2 Implementation
# ============================================================

"""
class CeleryJobManager(JobManager):
    '''
    Production-ready job manager using Celery + Redis.

    Migration steps from InMemoryJobManager:
    1. pip install celery redis
    2. Configure Redis connection
    3. Create Celery app and tasks
    4. Switch JOB_BACKEND environment variable
    5. No changes needed to API endpoints!

    Example:
        job_manager = CeleryJobManager(
            broker='redis://localhost:6379/0',
            backend='redis://localhost:6379/1'
        )
    '''

    def __init__(self, broker: str, backend: str):
        from celery import Celery

        self.app = Celery('sam2_jobs', broker=broker, backend=backend)

    def submit_job(self, job_type: str, task_func: Callable, params: Dict[str, Any]) -> str:
        # Submit to Celery
        task = self.app.send_task(job_type, kwargs=params)
        return task.id

    def get_job(self, job_id: str) -> Optional[Job]:
        from celery.result import AsyncResult

        result = AsyncResult(job_id, app=self.app)
        return Job(
            job_id=job_id,
            job_type='unknown',  # Could store in Redis
            status=JobStatus(result.state.lower()),
            result=result.result if result.ready() else None,
            ...
        )
"""
