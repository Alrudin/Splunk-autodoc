"""Integration tests for the jobs router and job processing workflow."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.models.job import Job
from app.models.upload import Upload


@pytest.fixture
def client(test_db: Session):
    """Create TestClient with test database."""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass  # Let test_db fixture handle cleanup

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.integration
class TestCreateJob:
    """Test POST /api/v1/uploads/{upload_id}/jobs endpoint."""

    def test_create_job_success(self, client: TestClient, test_db: Session, sample_upload: Upload):
        """Create job for upload, verify Job record created."""
        # TODO: POST /api/v1/uploads/{upload_id}/jobs
        # TODO: Assert status 201
        # TODO: Verify response contains job_id, status="pending"
        # TODO: Verify Job record exists in database
        pass

    def test_create_job_upload_not_found(self, client: TestClient):
        """Return 404 when upload_id doesn't exist."""
        # TODO: POST /api/v1/uploads/99999/jobs
        # TODO: Assert status 404
        pass

    def test_create_job_already_running(
        self, client: TestClient, test_db: Session, sample_upload: Upload
    ):
        """Prevent creating duplicate job when one is already running."""
        # TODO: Create a job with status="running" for sample_upload
        # TODO: POST /api/v1/uploads/{upload_id}/jobs
        # TODO: Assert status 409 (conflict) or job is reused
        pass


@pytest.mark.integration
class TestGetJob:
    """Test GET /api/v1/jobs/{job_id} endpoint."""

    def test_get_job_success(self, client: TestClient, sample_job: Job):
        """Get existing job, verify 200 response with status and logs."""
        # TODO: GET /api/v1/jobs/{job_id}
        # TODO: Assert status 200
        # TODO: Verify response contains id, upload_id, status, log, timestamps
        pass

    def test_get_job_not_found(self, client: TestClient):
        """Verify 404 for non-existent job ID."""
        # TODO: GET /api/v1/jobs/99999
        # TODO: Assert status 404
        pass


@pytest.mark.integration
class TestListJobs:
    """Test GET /api/v1/uploads/{upload_id}/jobs endpoint."""

    def test_list_jobs_for_upload(self, client: TestClient, sample_upload: Upload, sample_job: Job):
        """List all jobs for an upload."""
        # TODO: GET /api/v1/uploads/{upload_id}/jobs
        # TODO: Assert status 200
        # TODO: Verify response is array containing sample_job
        pass

    def test_list_jobs_filter_by_status(self, client: TestClient, test_db: Session, sample_upload: Upload):
        """Filter jobs by status parameter."""
        # TODO: Create jobs with different statuses (pending, running, completed, failed)
        # TODO: GET /api/v1/uploads/{upload_id}/jobs?status=completed
        # TODO: Assert only completed jobs returned
        pass


@pytest.mark.integration
class TestJobStatusTransitions:
    """Test job status lifecycle (pending → running → completed/failed)."""

    def test_job_status_pending_to_running(self, client: TestClient, test_db: Session, sample_job: Job):
        """Verify job can transition from pending to running."""
        # TODO: Verify sample_job.status == "pending"
        # TODO: Update job status to "running" (via PATCH endpoint if exists, or direct DB)
        # TODO: Verify status transition succeeded
        # TODO: Verify started_at timestamp is set
        pass

    def test_job_status_running_to_completed(self, client: TestClient, test_db: Session, sample_job: Job):
        """Verify job can transition from running to completed."""
        # TODO: Set sample_job.status = "running"
        # TODO: Update job status to "completed"
        # TODO: Verify status transition succeeded
        # TODO: Verify finished_at timestamp is set
        pass

    def test_job_status_running_to_failed(self, client: TestClient, test_db: Session, sample_job: Job):
        """Verify job can transition from running to failed."""
        # TODO: Set sample_job.status = "running"
        # TODO: Update job status to "failed" with error log
        # TODO: Verify status transition succeeded
        # TODO: Verify finished_at timestamp is set
        # TODO: Verify log contains error message
        pass


@pytest.mark.integration
class TestJobProcessing:
    """Test job processing workflow (integration with processor service)."""

    def test_job_processing_success(self, client: TestClient, test_db: Session, sample_upload: Upload, tmp_path):
        """Process job successfully, verify graph created."""
        # TODO: Mock or setup actual config files in sample_upload artifact
        # TODO: POST /api/v1/uploads/{upload_id}/jobs
        # TODO: Mock process_job_sync or run actual processing
        # TODO: Verify job status transitions to "completed"
        # TODO: Verify graph record created in database
        pass

    def test_job_processing_failure(self, client: TestClient, test_db: Session, sample_upload: Upload):
        """Process job with invalid config, verify failure handling."""
        # TODO: Setup sample_upload with malformed archive
        # TODO: POST /api/v1/uploads/{upload_id}/jobs
        # TODO: Verify job status transitions to "failed"
        # TODO: Verify error message in job.log
        pass


# TODO: Add more integration tests:
# - test_delete_job_prevent_if_running
# - test_job_timeout_handling
# - test_concurrent_job_creation
