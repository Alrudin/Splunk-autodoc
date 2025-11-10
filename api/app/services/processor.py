"""Job Processing Service.

This module orchestrates the complete job execution workflow:
1. Extract uploaded archive to work directory
2. Parse Splunk configuration files
3. Build canonical graph from parsed config
4. Generate findings/validation
5. Update job status and logs

This is the "glue" layer that connects storage, parser, resolver, and validator
services into a complete end-to-end pipeline.
"""

import logging
import traceback
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.upload import Upload
from app.services import storage
from app.services.parser import parse_splunk_config
from app.services.resolver import resolve_and_create_graph

logger = logging.getLogger(__name__)


def process_job(job_id: int, db_session: Session) -> None:
    """
    Execute complete job processing workflow.

    This is the main entry point for job execution. It can be called:
    - Synchronously from the create_job endpoint (MVP)
    - Asynchronously from a background worker (future enhancement)

    Workflow:
    1. Update job status to "running" with started_at timestamp
    2. Get upload record and extract archive to work directory
    3. Parse Splunk configuration files
    4. Build canonical graph from parsed config
    5. Generate findings/validation (future - validator service)
    6. Update job status to "completed" or "failed" with logs

    Args:
        job_id: Job ID to process
        db_session: SQLAlchemy session for database operations

    Raises:
        Exception: Any exception during processing is caught, logged, and job marked as failed
    """
    logger.info(f"Starting job processing for job_id={job_id}")

    # Get job record
    job = db_session.query(Job).filter(Job.id == job_id).first()
    if not job:
        logger.error(f"Job {job_id} not found")
        raise ValueError(f"Job {job_id} not found")

    # Get upload record
    upload = db_session.query(Upload).filter(Upload.id == job.upload_id).first()
    if not upload:
        logger.error(f"Upload {job.upload_id} not found for job {job_id}")
        raise ValueError(f"Upload {job.upload_id} not found")

    log_entries = []

    try:
        # Step 1: Update job status to "running"
        job.status = "running"
        job.started_at = datetime.now(UTC)
        db_session.commit()

        log_entries.append(f"[{datetime.now(UTC).isoformat()}] Job started")
        logger.info(f"Job {job_id} marked as running")

        # Step 2: Extract archive to work directory
        log_entries.append(f"[{datetime.now(UTC).isoformat()}] Extracting archive")
        logger.info(f"Extracting archive for job {job_id}")

        archive_path = Path(upload.storage_uri)
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive file not found: {upload.storage_uri}")

        work_dir = storage.get_work_directory(job_id)
        extracted_files = storage.extract_archive_safe(archive_path, work_dir)

        log_entries.append(
            f"[{datetime.now(UTC).isoformat()}] Extracted {len(extracted_files)} files"
        )
        logger.info(f"Extracted {len(extracted_files)} files to {work_dir}")

        # Handle common case where Splunk configs are under etc/ subdirectory
        # If work_dir/etc/system exists but work_dir/system doesn't, use etc/ as the base
        etc_dir = work_dir / "etc"
        has_etc_system = etc_dir.exists() and (etc_dir / "system").exists()
        has_root_system = (work_dir / "system").exists()
        if has_etc_system and not has_root_system:
            logger.info(
                f"Detected etc/ subdirectory structure, using {etc_dir} as work directory"
            )
            log_entries.append(
                f"[{datetime.now(UTC).isoformat()}] "
                f"Detected etc/ subdirectory, adjusting work directory"
            )
            work_dir = etc_dir

        # Step 3: Parse Splunk configuration
        log_entries.append(f"[{datetime.now(UTC).isoformat()}] Parsing Splunk configuration")
        logger.info(f"Parsing Splunk configuration for job {job_id}")

        parsed_config = parse_splunk_config(job_id, work_dir)

        log_entries.append(
            f"[{datetime.now(UTC).isoformat()}] Parsed config: "
            f"{len(parsed_config.inputs)} inputs, "
            f"{len(parsed_config.outputs)} outputs, "
            f"{len(parsed_config.props)} props, "
            f"{len(parsed_config.transforms)} transforms"
        )
        logger.info(
            f"Parsed config for job {job_id}: "
            f"{len(parsed_config.inputs)} inputs, {len(parsed_config.outputs)} outputs"
        )

        # Step 4: Build canonical graph
        log_entries.append(f"[{datetime.now(UTC).isoformat()}] Building canonical graph")
        logger.info(f"Building canonical graph for job {job_id}")

        graph = resolve_and_create_graph(job_id, parsed_config, db_session)

        log_entries.append(
            f"[{datetime.now(UTC).isoformat()}] Created graph with ID {graph.id}: "
            f"{graph.json_blob['meta']['host_count']} hosts, "
            f"{graph.json_blob['meta']['edge_count']} edges"
        )
        logger.info(
            f"Created graph {graph.id} for job {job_id}: "
            f"{graph.json_blob['meta']['host_count']} hosts, "
            f"{graph.json_blob['meta']['edge_count']} edges"
        )

        # Step 5: Generate findings (future - validator service)
        # TODO: Implement validator service and call here
        # findings = validator.validate_graph(graph, parsed_config)
        # for finding in findings:
        #     db_session.add(finding)

        # Step 6: Mark job as completed
        job.status = "completed"
        job.finished_at = datetime.now(UTC)
        log_entries.append(f"[{datetime.now(UTC).isoformat()}] Job completed successfully")
        job.log = "\n".join(log_entries)

        db_session.commit()
        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        # Log error and mark job as failed
        error_msg = f"Error processing job {job_id}: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())

        log_entries.append(f"[{datetime.now(UTC).isoformat()}] ERROR: {str(e)}")
        log_entries.append(f"[{datetime.now(UTC).isoformat()}] Traceback:")
        log_entries.append(traceback.format_exc())

        job.status = "failed"
        job.finished_at = datetime.now(UTC)
        job.log = "\n".join(log_entries)

        db_session.commit()
        # Exception is logged and job status updated; no need to re-raise since caller suppresses exceptions.


def process_job_sync(job_id: int, db_session: Session) -> None:
    """
    Synchronous wrapper for process_job.

    This is intended for MVP usage where jobs are processed inline.
    For production with background workers, use process_job_async instead.

    Args:
        job_id: Job ID to process
        db_session: SQLAlchemy session for database operations

    Raises:
        Exception: Any exception during processing
    """
    logger.info(f"Processing job {job_id} synchronously")
    process_job(job_id, db_session)
