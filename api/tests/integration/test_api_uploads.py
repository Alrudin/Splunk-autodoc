"""Integration tests for the uploads router with file upload handling."""

import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.models.project import Project
from app.models.upload import Upload
from tests.fixtures.splunk_configs import create_hf_config, create_uf_config


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


def create_test_zip_archive(tmp_path: Path, name: str = "test.zip") -> io.BytesIO:
    """Create a minimal valid ZIP archive in memory for testing."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("etc/system/local/inputs.conf", "[monitor:///var/log]\nindex = main\n")
        zf.writestr("etc/system/local/outputs.conf", "[tcpout]\nserver = idx1:9997\n")
    zip_buffer.seek(0)
    return zip_buffer


@pytest.mark.integration
class TestCreateUpload:
    """Test POST /api/v1/projects/{project_id}/uploads endpoint."""

    def test_create_upload_success(
        self, client: TestClient, test_db: Session, sample_project: Project, tmp_path: Path
    ):
        """Upload valid ZIP file, verify 201 response and Upload record created."""
        # TODO: Create test ZIP archive
        # TODO: POST /api/v1/projects/{project_id}/uploads with multipart file
        # TODO: Assert status 201
        # TODO: Verify response contains upload_id, filename, size, status
        # TODO: Verify Upload record exists in database
        # TODO: Verify artifact file saved to storage
        pass

    def test_create_upload_project_not_found(self, client: TestClient, tmp_path: Path):
        """Return 404 when project_id doesn't exist."""
        # TODO: Create test ZIP archive
        # TODO: POST /api/v1/projects/99999/uploads
        # TODO: Assert status 404
        pass

    def test_create_upload_invalid_file_type(
        self, client: TestClient, sample_project: Project
    ):
        """Reject non-ZIP/tar.gz file with 400 error."""
        # TODO: Create text file or invalid archive
        # TODO: POST /api/v1/projects/{project_id}/uploads
        # TODO: Assert status 400
        # TODO: Verify error message mentions invalid file type
        pass

    def test_create_upload_file_too_large(
        self, client: TestClient, sample_project: Project
    ):
        """Reject file exceeding size limit with 413 error."""
        # TODO: Create large file exceeding MAX_UPLOAD_SIZE
        # TODO: POST /api/v1/projects/{project_id}/uploads
        # TODO: Assert status 413
        pass

    def test_create_upload_missing_file(self, client: TestClient, sample_project: Project):
        """Return 422 when file field is missing."""
        # TODO: POST /api/v1/projects/{project_id}/uploads without file
        # TODO: Assert status 422 (validation error)
        pass


@pytest.mark.integration
class TestGetUpload:
    """Test GET /api/v1/uploads/{upload_id} endpoint."""

    def test_get_upload_success(self, client: TestClient, sample_upload: Upload):
        """Get existing upload, verify 200 response."""
        # TODO: GET /api/v1/uploads/{upload_id}
        # TODO: Assert status 200
        # TODO: Verify response contains id, project_id, filename, size, status, storage_uri
        pass

    def test_get_upload_not_found(self, client: TestClient):
        """Verify 404 for non-existent upload ID."""
        # TODO: GET /api/v1/uploads/99999
        # TODO: Assert status 404
        pass


@pytest.mark.integration
class TestListUploads:
    """Test GET /api/v1/projects/{project_id}/uploads endpoint."""

    def test_list_uploads_for_project(
        self, client: TestClient, sample_project: Project, sample_upload: Upload
    ):
        """List all uploads for a project."""
        # TODO: GET /api/v1/projects/{project_id}/uploads
        # TODO: Assert status 200
        # TODO: Verify response is array containing sample_upload
        pass

    def test_list_uploads_empty(self, client: TestClient, sample_project: Project):
        """Verify empty array when project has no uploads."""
        # TODO: GET /api/v1/projects/{project_id}/uploads
        # TODO: Assert status 200
        # TODO: Assert response is empty array
        pass

    def test_list_uploads_filter_by_status(
        self, client: TestClient, test_db: Session, sample_project: Project
    ):
        """Filter uploads by status parameter."""
        # TODO: Create uploads with different statuses (uploaded, processing, completed, failed)
        # TODO: GET /api/v1/projects/{project_id}/uploads?status=completed
        # TODO: Assert only completed uploads returned
        pass


@pytest.mark.integration
class TestDeleteUpload:
    """Test DELETE /api/v1/uploads/{upload_id} endpoint."""

    def test_delete_upload_success(
        self, client: TestClient, test_db: Session, sample_upload: Upload, temp_storage_root: Path
    ):
        """Delete upload, verify 204 response and cascade deletion."""
        # TODO: Verify artifact file exists in storage
        # TODO: DELETE /api/v1/uploads/{upload_id}
        # TODO: Assert status 204
        # TODO: Verify Upload record deleted from database
        # TODO: Verify artifact file deleted from storage
        pass

    def test_delete_upload_not_found(self, client: TestClient):
        """Verify 404 for non-existent upload ID."""
        # TODO: DELETE /api/v1/uploads/99999
        # TODO: Assert status 404
        pass

    def test_delete_upload_cascade_jobs(
        self, client: TestClient, test_db: Session, sample_upload: Upload
    ):
        """Verify deleting upload also deletes associated jobs."""
        # TODO: Create job associated with sample_upload
        # TODO: DELETE /api/v1/uploads/{upload_id}
        # TODO: Assert status 204
        # TODO: Verify job also deleted from database
        pass


@pytest.mark.integration
class TestUploadFileHandling:
    """Test archive extraction and file validation."""

    def test_upload_zip_extraction(
        self, client: TestClient, test_db: Session, sample_project: Project, tmp_path: Path
    ):
        """Upload ZIP file, verify extraction to work directory."""
        # TODO: Create ZIP with golden config (create_uf_config)
        # TODO: POST /api/v1/projects/{project_id}/uploads
        # TODO: Verify upload created
        # TODO: Verify archive extracted to storage_root/artifacts/{upload_id}/
        # TODO: Verify extracted files readable
        pass

    def test_upload_tar_gz_extraction(
        self, client: TestClient, test_db: Session, sample_project: Project, tmp_path: Path
    ):
        """Upload tar.gz file, verify extraction."""
        # TODO: Create tar.gz with golden config
        # TODO: POST /api/v1/projects/{project_id}/uploads
        # TODO: Verify upload created
        # TODO: Verify archive extracted correctly
        pass

    def test_upload_path_traversal_prevention(
        self, client: TestClient, sample_project: Project, tmp_path: Path
    ):
        """Reject archive with path traversal attempts."""
        # TODO: Create malicious ZIP with ../../../etc/passwd entry
        # TODO: POST /api/v1/projects/{project_id}/uploads
        # TODO: Assert status 400
        # TODO: Verify error message mentions security issue
        pass

    def test_upload_archive_bomb_prevention(
        self, client: TestClient, sample_project: Project
    ):
        """Reject archive with excessive compression ratio (zip bomb)."""
        # TODO: Create ZIP with high compression ratio
        # TODO: POST /api/v1/projects/{project_id}/uploads
        # TODO: Assert status 400 or 413
        pass


# TODO: Add more integration tests:
# - test_upload_concurrent_uploads_same_project
# - test_upload_resume_interrupted_upload
# - test_upload_validate_archive_content
