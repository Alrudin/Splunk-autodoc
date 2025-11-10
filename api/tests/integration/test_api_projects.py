"""Integration tests for the projects router using FastAPI TestClient."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.models.project import Project


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
def test_create_project_success(client: TestClient, test_db: Session):
    """Create project with name and labels, verify 201 response."""
    response = client.post(
        "/api/v1/projects",
        json={"name": "Test Project", "labels": ["test", "sample"]},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["labels"] == ["test", "sample"]
    assert "id" in data
    assert "created_at" in data

    # Verify database record
    project = test_db.query(Project).filter(Project.id == data["id"]).first()
    assert project is not None
    assert project.name == "Test Project"


@pytest.mark.integration
def test_list_projects_empty(client: TestClient):
    """Verify empty array when no projects."""
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.integration
def test_list_projects_multiple(client: TestClient, sample_project: Project):
    """Create multiple projects, verify all returned."""
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(p["id"] == sample_project.id for p in data)


@pytest.mark.integration
def test_get_project_success(client: TestClient, sample_project: Project):
    """Get existing project, verify 200 response."""
    response = client.get(f"/api/v1/projects/{sample_project.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_project.id
    assert data["name"] == sample_project.name


@pytest.mark.integration
def test_get_project_not_found(client: TestClient):
    """Verify 404 for non-existent ID."""
    response = client.get("/api/v1/projects/99999")
    assert response.status_code == 404


@pytest.mark.integration
def test_delete_project_success(client: TestClient, test_db: Session, sample_project: Project):
    """Delete existing project, verify 204 response."""
    project_id = sample_project.id
    response = client.delete(f"/api/v1/projects/{project_id}")
    assert response.status_code == 204

    # Verify database record is deleted
    project = test_db.query(Project).filter(Project.id == project_id).first()
    assert project is None


@pytest.mark.integration
def test_delete_project_not_found(client: TestClient):
    """Verify 404 for non-existent ID."""
    response = client.delete("/api/v1/projects/99999")
    assert response.status_code == 404


# TODO: Add more integration tests:
# - test_update_project_name
# - test_update_project_labels
# - test_delete_project_cascade (with uploads/graphs)
