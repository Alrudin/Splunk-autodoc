"""Pytest configuration with shared fixtures for all tests."""

import shutil
import tarfile
import zipfile
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base
from app.models.finding import Finding
from app.models.graph import Graph
from app.models.job import Job
from app.models.project import Project
from app.models.upload import Upload

# Import golden config creators
from tests.fixtures.splunk_configs import (
    create_ambiguous_routing_config,
    create_dangling_output_config,
    create_hec_config,
    create_hf_config,
    create_idx_config,
    create_indexer_discovery_config,
    create_precedence_test_config,
    create_uf_config,
)


@pytest.fixture(scope="function")
def test_db_engine():
    """Create in-memory SQLite engine for fast tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},  # Allow TestClient to use connection across threads
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """Provide clean database session for each test with automatic rollback."""
    connection = test_db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)

    # Enable savepoints so that router commits don't conflict with test rollback
    session.begin_nested()

    # After each commit/rollback in the tested code, start a new savepoint
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def test_db(test_db_session) -> Session:
    """Alias for test_db_session for convenience."""
    return test_db_session


@pytest.fixture(scope="function")
def temp_storage_root(tmp_path: Path, monkeypatch) -> Path:
    """Create temporary directory for file operations."""
    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "storage_root", str(storage_root))
    return storage_root


def create_archive_from_config(
    config_creator_func,
    storage_root: Path,
    upload_id: int,
    archive_format: str = "zip",
) -> Path:
    """
    Helper to create a real archive file from golden config creator function.

    Args:
        config_creator_func: Function from splunk_configs.py (e.g., create_uf_config)
        storage_root: Root storage directory
        upload_id: Upload ID for organizing artifacts
        archive_format: "zip" or "tar.gz"

    Returns:
        Path to created archive file
    """
    # Create config directory structure
    config_dir = storage_root / "temp" / f"config_{upload_id}"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Generate config files using golden config creator
    config_creator_func(config_dir)

    # Create artifacts directory for upload
    artifacts_dir = storage_root / "artifacts" / str(upload_id)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Create archive
    if archive_format == "zip":
        archive_path = artifacts_dir / "upload.zip"
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in config_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(config_dir)
                    zipf.write(file_path, arcname)
    elif archive_format == "tar.gz":
        archive_path = artifacts_dir / "upload.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tarf:
            tarf.add(config_dir, arcname=".")
    else:
        raise ValueError(f"Unsupported archive format: {archive_format}")

    # Clean up temp config directory
    shutil.rmtree(config_dir)

    return archive_path


@pytest.fixture(scope="function")
def create_test_archive():
    """
    Fixture factory for creating test archives with golden configs.

    Usage in tests:
        archive_path = create_test_archive(
            create_uf_config,
            temp_storage_root,
            upload_id=1,
            archive_format="zip"
        )
    """
    return create_archive_from_config


@pytest.fixture(scope="function")
def sample_project(test_db: Session) -> Project:
    """Create and return a Project instance in the database."""
    project = Project(
        name="Test Project",
        labels=["test", "sample"],
    )
    test_db.add(project)
    test_db.commit()
    test_db.refresh(project)
    return project


@pytest.fixture(scope="function")
def sample_upload(
    test_db: Session, sample_project: Project, temp_storage_root: Path
) -> Upload:
    """Create Upload instance with real archive file in temp storage."""
    # Create real archive using UF config
    archive_path = create_archive_from_config(
        create_uf_config, temp_storage_root, upload_id=1, archive_format="zip"
    )

    # Get file size
    file_size = archive_path.stat().st_size

    upload = Upload(
        project_id=sample_project.id,
        filename="test_config.zip",
        size=file_size,
        status="completed",
        storage_uri=str(archive_path),
    )
    test_db.add(upload)
    test_db.commit()
    test_db.refresh(upload)
    return upload


@pytest.fixture(scope="function")
def sample_job(test_db: Session, sample_upload: Upload) -> Job:
    """Create Job instance linked to sample_upload."""
    job = Job(
        upload_id=sample_upload.id,
        status="completed",
        log="Job completed successfully",
    )
    test_db.add(job)
    test_db.commit()
    test_db.refresh(job)
    return job


@pytest.fixture(scope="function")
def sample_graph(test_db: Session, sample_project: Project, sample_job: Job) -> Graph:
    """Create Graph instance with minimal canonical JSON."""
    graph = Graph(
        project_id=sample_project.id,
        job_id=sample_job.id,
        version="1.0",
        json_blob={
            "hosts": [
                {
                    "id": "host1",
                    "roles": ["universal_forwarder"],
                    "labels": [],
                    "apps": ["Splunk_TA_nix"],
                }
            ],
            "edges": [
                {
                    "src_host": "host1",
                    "dst_host": "indexer1",
                    "protocol": "splunktcp",
                    "sources": ["/var/log/messages"],
                    "sourcetypes": ["syslog"],
                    "indexes": ["main"],
                    "filters": [],
                    "drop_rules": [],
                    "tls": False,
                    "weight": 1,
                    "confidence": "explicit",
                }
            ],
            "meta": {
                "generator": "test",
                "generated_at": "2025-01-01T00:00:00Z",
                "host_count": 1,
                "edge_count": 1,
                "source_hosts": ["host1"],
                "traceability": {},
            },
        },
        meta={},
    )
    test_db.add(graph)
    test_db.commit()
    test_db.refresh(graph)
    return graph


@pytest.fixture(scope="function")
def sample_finding(test_db: Session, sample_graph: Graph) -> Finding:
    """Create Finding instance linked to sample_graph."""
    finding = Finding(
        graph_id=sample_graph.id,
        code="DANGLING_OUTPUT",
        severity="error",
        message="Edge to placeholder host detected",
        context={"src_host": "host1", "dst_host": "unknown_destination"},
    )
    test_db.add(finding)
    test_db.commit()
    test_db.refresh(finding)
    return finding
