"""Integration tests for uploads API with real archive handling.""""""Integration tests for uploads API endpoint.""""""Integration tests for uploads API.""""""Integration tests for the uploads router with file upload handling."""



from pathlib import Path



import pytestfrom io import BytesIO

from fastapi.testclient import TestClient

from sqlalchemy.orm import Sessionfrom pathlib import Path



from app.database import get_dbfrom io import BytesIOimport io

from app.main import app

from app.models.project import Projectimport pytest

from app.models.upload import Upload

from tests.fixtures.splunk_configs import create_hf_config, create_uf_configfrom fastapi import statusfrom pathlib import Pathimport zipfile



from fastapi.testclient import TestClient

@pytest.fixture

def client(test_db: Session):from sqlalchemy.orm import Session

    """Create TestClient with test database."""



    def override_get_db():

        try:from app.database import get_dbimport pytestimport pytest

            yield test_db

        finally:from app.main import app

            pass  # Let test_db fixture handle cleanup

from app.models.project import Projectfrom fastapi import statusfrom fastapi.testclient import TestClient

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)from app.models.upload import Upload

    app.dependency_overrides.clear()

from fastapi.testclient import TestClientfrom sqlalchemy.orm import Session



@pytest.mark.integration

class TestUploadWithRealArchives:

    """Test uploads with real archive files created from golden configs."""@pytest.fixturefrom sqlalchemy.orm import Session



    def test_sample_upload_has_real_file(def client(test_db_session: Session):

        self, sample_upload: Upload, temp_storage_root: Path

    ):    """FastAPI test client with database override."""from app.database import get_db

        """Verify sample_upload fixture creates real archive file."""

        archive_path = Path(sample_upload.storage_uri)

        assert archive_path.exists(), f"Archive not found: {archive_path}"

        assert archive_path.stat().st_size > 0, "Archive file is empty"    def override_get_db():from app.database import get_dbfrom app.main import app

        assert sample_upload.size == archive_path.stat().st_size

        try:

    def test_create_archive_from_uf_config(

        self, temp_storage_root: Path, create_test_archive            yield test_db_sessionfrom app.main import appfrom app.models.project import Project

    ):

        """Create ZIP archive from UF golden config."""        finally:

        archive_path = create_test_archive(

            create_uf_config, temp_storage_root, upload_id=100, archive_format="zip"            pass  # Don't close shared test sessionfrom app.models.project import Project

        )

        assert archive_path.exists()

        assert archive_path.suffix == ".zip"

        assert archive_path.stat().st_size > 0    app.dependency_overrides[get_db] = override_get_db  # noqa: B008from app.models.upload import Upload



    def test_create_archive_from_hf_config(    yield TestClient(app)

        self, temp_storage_root: Path, create_test_archive

    ):    app.dependency_overrides.clear()@pytest.fixture

        """Create tar.gz archive from HF golden config."""

        archive_path = create_test_archive(

            create_hf_config, temp_storage_root, upload_id=101, archive_format="tar.gz"

        )def client(test_db: Session):

        assert archive_path.exists()

        assert archive_path.name == "upload.tar.gz"@pytest.mark.integration

        assert archive_path.stat().st_size > 0

class TestCreateUpload:@pytest.fixture    """Create TestClient with test database."""

    def test_archive_contains_conf_files(

        self, temp_storage_root: Path, create_test_archive    """Test POST /api/v1/uploads endpoint."""

    ):

        """Verify archive contains expected .conf files."""def client(test_db_session: Session):

        import zipfile

    def test_create_upload_success(

        archive_path = create_test_archive(

            create_uf_config, temp_storage_root, upload_id=102, archive_format="zip"        self, client: TestClient, sample_project: Project, tmp_path: Path    """FastAPI test client with database override."""    def override_get_db():

        )

    ):

        with zipfile.ZipFile(archive_path, "r") as zipf:

            filenames = zipf.namelist()        """Upload valid .zip file, verify Upload record created."""        try:

            # UF config should have inputs.conf and outputs.conf

            assert any("inputs.conf" in f for f in filenames)        # TODO: Create sample .zip file with Splunk conf files

            assert any("outputs.conf" in f for f in filenames)

        # files = {"file": ("config.zip", zip_bytes, "application/zip")}    def override_get_db():            yield test_db



@pytest.mark.integration        # response = client.post(

class TestCreateUpload:

    """Test POST /api/v1/uploads endpoint (placeholder - needs router implementation)."""        #     "/api/v1/uploads",        try:        finally:



    def test_create_upload_success(        #     files=files,

        self, client: TestClient, sample_project: Project, temp_storage_root: Path

    ):        #     data={"project_id": sample_project.id}            yield test_db_session            pass  # Let test_db fixture handle cleanup

        """Upload valid .zip file, verify Upload record created."""

        # TODO: Implement when uploads router is complete        # )

        # Use create_test_archive to build real archive

        # POST to /api/v1/uploads with file and project_id        # TODO: Assert response.status_code == 201        finally:

        # Assert status 201, response contains upload_id

        # Verify Upload record exists in database with correct storage_uri        # TODO: Verify response.json() contains upload_id

        pass

        # TODO: Query DB to verify Upload record exists            pass  # Don't close shared test session    app.dependency_overrides[get_db] = override_get_db



@pytest.mark.integration        # TODO: Verify file is saved to storage

class TestGetUpload:

    """Test GET /api/v1/uploads/{upload_id} endpoint."""        pass    yield TestClient(app)



    def test_get_upload_success(self, client: TestClient, sample_upload: Upload):

        """Retrieve upload by ID, verify real file path returned."""

        # TODO: GET /api/v1/uploads/{upload_id}    def test_create_upload_tar_gz(    app.dependency_overrides[get_db] = override_get_db  # noqa: B008    app.dependency_overrides.clear()

        # Assert status 200

        # Verify response contains storage_uri pointing to real file        self, client: TestClient, sample_project: Project, tmp_path: Path

        # Verify file exists at storage_uri path

        pass    ):    yield TestClient(app)



        """Upload valid .tar.gz file."""

@pytest.mark.integration

class TestListUploads:        # TODO: Create sample .tar.gz file    app.dependency_overrides.clear()

    """Test GET /api/v1/projects/{project_id}/uploads endpoint."""

        # files = {"file": ("config.tar.gz", tar_bytes, "application/gzip")}

    def test_list_uploads_for_project(

        self, client: TestClient, sample_project: Project, sample_upload: Upload        # response = client.post("/api/v1/uploads", files=files, data={...})def create_sample_zip() -> bytes:

    ):

        """List all uploads for a project."""        # TODO: Assert status 201

        # TODO: GET /api/v1/projects/{project_id}/uploads

        # Assert status 200        pass    """Create a sample ZIP file with valid magic bytes."""

        # Verify response includes sample_upload with correct storage info

        pass



    def test_create_upload_invalid_extension(@pytest.mark.integration    buffer = io.BytesIO()

@pytest.mark.integration

class TestDeleteUpload:        self, client: TestClient, sample_project: Project

    """Test DELETE /api/v1/uploads/{upload_id} endpoint."""

    ):class TestCreateUpload:    with zipfile.ZipFile(buffer, "w") as zf:

    def test_delete_upload_removes_file(

        self, client: TestClient, sample_upload: Upload, temp_storage_root: Path        """Reject file with invalid extension."""

    ):

        """Verify uploaded archive file is removed from storage."""        # TODO: Create .exe file bytes    """Test POST /api/v1/uploads endpoint."""        zf.writestr("test.txt", "content")

        archive_path = Path(sample_upload.storage_uri)

        assert archive_path.exists(), "Archive should exist before delete"        # files = {"file": ("malware.exe", b"MZ...", "application/x-msdownload")}



        # TODO: DELETE /api/v1/uploads/{upload_id}        # response = client.post("/api/v1/uploads", files=files, data={...})    return buffer.getvalue()

        # Assert status 204

        # Verify archive_path no longer exists        # TODO: Assert status 400

        # Verify artifacts/{upload_id}/ directory is removed

        pass        # TODO: Verify error message mentions invalid file type    def test_create_upload_success(


        pass

        self, client: TestClient, sample_project: Project, tmp_path: Path

    def test_create_upload_invalid_magic_bytes(

        self, client: TestClient, sample_project: Project    ):@pytest.mark.integration

    ):

        """Reject file with mismatched magic bytes."""        """Upload valid .zip file, verify Upload record created."""def test_placeholder_uploads():

        # TODO: Create text file named file.zip

        # files = {"file": ("fake.zip", b"not a zip file", "application/zip")}        # TODO: Create sample .zip file with Splunk conf files    """Placeholder test to ensure test discovery works."""

        # response = client.post("/api/v1/uploads", files=files, data={...})

        # TODO: Assert status 400        # TODO: POST to /api/v1/uploads with file and project_id    assert True

        pass

        # TODO: Assert status 201, response contains upload_id

    def test_create_upload_project_not_found(self, client: TestClient):

        """Return 404 when project_id doesn't exist."""        # TODO: Verify Upload record exists in database

        # TODO: Create valid .zip file

        # response = client.post(        # TODO: Verify file is saved to storage# TODO: Implement upload integration tests:

        #     "/api/v1/uploads",

        #     files={...},        pass# - test_create_upload_success

        #     data={"project_id": 99999}

        # )# - test_create_upload_project_not_found

        # TODO: Assert status 404

        pass    def test_create_upload_tar_gz(# - test_create_upload_invalid_extension



        self, client: TestClient, sample_project: Project, tmp_path: Path# - test_get_upload_success

@pytest.mark.integration

class TestGetUpload:    ):# - test_get_upload_not_found

    """Test GET /api/v1/uploads/{upload_id} endpoint."""

        """Upload valid .tar.gz file."""

    def test_get_upload_success(self, client: TestClient, sample_upload: Upload):        # TODO: Create sample .tar.gz file

        """Retrieve upload by ID."""        # TODO: POST to /api/v1/uploads

        # response = client.get(f"/api/v1/uploads/{sample_upload.id}")        # TODO: Assert status 201

        # TODO: Assert status 200        pass

        # TODO: Verify response contains filename, project_id, created_at

        pass    def test_create_upload_invalid_extension(

        self, client: TestClient, sample_project: Project

    def test_get_upload_not_found(self, client: TestClient):    ):

        """Return 404 for nonexistent upload."""        """Reject file with invalid extension."""

        # response = client.get("/api/v1/uploads/99999")        # TODO: Create .exe file

        # TODO: Assert status 404        # TODO: POST to /api/v1/uploads

        pass        # TODO: Assert status 400, error message mentions invalid file type

        pass



@pytest.mark.integration    def test_create_upload_invalid_magic_bytes(

class TestListUploads:        self, client: TestClient, sample_project: Project, tmp_path: Path

    """Test GET /api/v1/projects/{project_id}/uploads endpoint."""    ):

        """Reject file with mismatched magic bytes."""

    def test_list_uploads_for_project(        # TODO: Create text file named file.zip

        self, client: TestClient, sample_project: Project, sample_upload: Upload        # TODO: POST to /api/v1/uploads

    ):        # TODO: Assert status 400, error mentions file validation

        """List all uploads for a project."""        pass

        # response = client.get(f"/api/v1/projects/{sample_project.id}/uploads")

        # TODO: Assert status 200    def test_create_upload_project_not_found(self, client: TestClient, tmp_path: Path):

        # TODO: Verify response is list containing sample_upload.id        """Return 404 when project_id doesn't exist."""

        pass        # TODO: Create valid .zip file

        # TODO: POST with nonexistent project_id

    def test_list_uploads_empty_project(        # TODO: Assert status 404

        self, client: TestClient, sample_project: Project        pass

    ):

        """Return empty list for project with no uploads."""    def test_create_upload_missing_file(

        # response = client.get(f"/api/v1/projects/{sample_project.id}/uploads")        self, client: TestClient, sample_project: Project

        # TODO: Assert status 200    ):

        # TODO: Verify response.json() == []        """Return 400 when no file provided."""

        pass        # TODO: POST to /api/v1/uploads with project_id but no file

        # TODO: Assert status 400

        pass

@pytest.mark.integration

class TestDeleteUpload:

    """Test DELETE /api/v1/uploads/{upload_id} endpoint."""@pytest.mark.integration

class TestGetUpload:

    def test_delete_upload_success(    """Test GET /api/v1/uploads/{upload_id} endpoint."""

        self, client: TestClient, sample_upload: Upload, test_db_session: Session

    ):    def test_get_upload_success(self, client: TestClient, sample_upload: Upload):

        """Delete upload and verify cascade."""        """Retrieve upload by ID."""

        # response = client.delete(f"/api/v1/uploads/{sample_upload.id}")        # TODO: GET /api/v1/uploads/{upload_id}

        # TODO: Assert status 204        # TODO: Assert status 200

        # TODO: Query DB to verify Upload is deleted        # TODO: Verify response contains filename, project_id, created_at

        # TODO: Verify related Jobs are deleted (cascade)        pass

        pass

    def test_get_upload_not_found(self, client: TestClient):

    def test_delete_upload_not_found(self, client: TestClient):        """Return 404 for nonexistent upload."""

        """Return 404 for nonexistent upload."""        # TODO: GET /api/v1/uploads/99999

        # response = client.delete("/api/v1/uploads/99999")        # TODO: Assert status 404

        # TODO: Assert status 404        pass

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
        # TODO: Verify response is list containing sample_upload
        pass

    def test_list_uploads_empty_project(
        self, client: TestClient, sample_project: Project
    ):
        """Return empty list for project with no uploads."""
        # TODO: GET /api/v1/projects/{project_id}/uploads
        # TODO: Assert status 200
        # TODO: Verify response is empty list
        pass

    def test_list_uploads_project_not_found(self, client: TestClient):
        """Return 404 for nonexistent project."""
        # TODO: GET /api/v1/projects/99999/uploads
        # TODO: Assert status 404
        pass


@pytest.mark.integration
class TestDeleteUpload:
    """Test DELETE /api/v1/uploads/{upload_id} endpoint."""

    def test_delete_upload_success(self, client: TestClient, sample_upload: Upload):
        """Delete upload and verify cascade."""
        # TODO: DELETE /api/v1/uploads/{upload_id}
        # TODO: Assert status 204
        # TODO: Verify Upload record is deleted from DB
        # TODO: Verify related Jobs are deleted (cascade)
        pass

    def test_delete_upload_not_found(self, client: TestClient):
        """Return 404 for nonexistent upload."""
        # TODO: DELETE /api/v1/uploads/99999
        # TODO: Assert status 404
        pass

    def test_delete_upload_removes_files(
        self, client: TestClient, sample_upload: Upload, temp_storage_root: Path
    ):
        """Verify uploaded files are removed from storage."""
        # TODO: DELETE /api/v1/uploads/{upload_id}
        # TODO: Assert artifacts/{upload_id}/ directory is deleted
        pass
