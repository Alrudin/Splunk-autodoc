from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db  # type: ignore
from app.models.job import Job  # type: ignore
from app.models.upload import Upload  # type: ignore
from app.schemas import JobResponse  # type: ignore
from app.services.processor import process_job_sync  # type: ignore

router = APIRouter(tags=["jobs"])


@router.post(
    "/uploads/{upload_id}/jobs",
    status_code=status.HTTP_201_CREATED,
    response_model=JobResponse,
)
def create_job(upload_id: int, db: Session = Depends(get_db)) -> JobResponse:  # noqa: B008
    """
    Create a new job to process an upload.

    Args:
        upload_id: ID of the upload to process
        db: Database session

    Returns:
        Created job with pending status

    Raises:
        HTTPException: 404 if upload not found, 400 if upload already processing
    """
    # Verify upload exists
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

    # Optional: Check for duplicate pending/running jobs
    existing_job = (
        db.query(Job)
        .filter(Job.upload_id == upload_id, Job.status.in_(["pending", "running"]))
        .first()
    )

    if existing_job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload already has a {existing_job.status} job (ID: {existing_job.id})",
        )

    try:
        # Create job record with pending status
        job = Job(
            upload_id=upload_id, status="pending", log=None, started_at=None, finished_at=None
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Process job synchronously (MVP approach)
        # For production, consider using background worker (Redis + RQ/Celery)
        try:
            process_job_sync(job.id, db)
            db.refresh(job)  # Refresh to get updated status and logs
        except Exception as ex:
            # Job processor already marks job as failed and logs error
            # Log the exception for debugging purposes
            import logging
            logging.exception("Error during job processing or refresh")
        # Return ORM model instance directly; Pydantic schema handles serialization and avoids cycles
        return job

        return response
    except Exception as e:
        db.rollback()
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job: {str(e)}",
        )


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobResponse:  # noqa: B008
    """
    Get job status and details by ID.

    Args:
        job_id: Job ID
        db: Database session

    Returns:
        Job with status, logs, timestamps, and related upload/graph

    Raises:
        HTTPException: 404 if job not found
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Job includes:
    # - status: pending, running, completed, failed
    # - log: execution logs, errors, warnings
    # - started_at, finished_at: timestamps
    # - upload: related upload (via relationship with lazy="selectin")
    # - graph: related graph if completed (one-to-one relationship)

    return job
