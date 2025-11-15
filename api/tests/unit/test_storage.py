"""Unit tests for the storage service."""

import io
import sys
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import UploadFile

from app.routers.uploads import validate_file_extension
from app.services.storage import (
    # Archive extraction
    CHUNK_SIZE,
    # Cleanup
    cleanup_directory,
    cleanup_upload,
    cleanup_work,
    # Directory management
    ensure_directory,
    extract_archive_safe,
    generate_storage_uri,
    get_exports_directory,
    get_file_size,
    get_graphs_directory,
    get_storage_root,
    get_upload_directory,
    get_work_directory,
    # Upload handling
    save_upload_file,
    # Path safety
    validate_archive_content,
    validate_path_safety,
)


@pytest.mark.unit
class TestArchiveExtraction:
    """Test archive extraction (zip, tar.gz)."""

    def test_extract_archive_zip(self, tmp_path: Path, temp_storage_root: Path):
        """Extract .zip archive, verify directory structure."""
        # Create a real .zip file with sample .conf files
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("apps/TA-example/local/inputs.conf", "[monitor://var/log]\nindex=main\n")
            zf.writestr("system/local/outputs.conf", "[tcpout]\ndefaultGroup=indexers\n")

        # Extract archive
        extract_dir = temp_storage_root / "extract"
        extracted_files = extract_archive_safe(zip_path, extract_dir)

        # Assert extraction directory exists
        assert extract_dir.exists()
        # Verify expected files are present
        assert (extract_dir / "apps/TA-example/local/inputs.conf").exists()
        assert (extract_dir / "system/local/outputs.conf").exists()
        # Verify file contents match
        content = (extract_dir / "apps/TA-example/local/inputs.conf").read_text()
        assert "[monitor://var/log]" in content
        # Verify function returns list of paths
        assert len(extracted_files) == 2
        assert all(isinstance(p, Path) for p in extracted_files)

    def test_extract_archive_tar_gz(self, tmp_path: Path, temp_storage_root: Path):
        """Extract .tar.gz archive, verify directory structure."""
        # Create a real .tar.gz file with sample .conf files
        tar_gz_path = tmp_path / "test.tar.gz"
        with tarfile.open(tar_gz_path, "w:gz") as tf:
            # Create in-memory conf files
            inputs_data = b"[monitor://var/log]\nindex=main\n"
            outputs_data = b"[tcpout]\ndefaultGroup=indexers\n"

            # Add inputs.conf
            inputs_info = tarfile.TarInfo(name="apps/TA-example/local/inputs.conf")
            inputs_info.size = len(inputs_data)
            tf.addfile(inputs_info, io.BytesIO(inputs_data))

            # Add outputs.conf
            outputs_info = tarfile.TarInfo(name="system/local/outputs.conf")
            outputs_info.size = len(outputs_data)
            tf.addfile(outputs_info, io.BytesIO(outputs_data))

        # Extract archive
        extract_dir = temp_storage_root / "extract"
        extracted_files = extract_archive_safe(tar_gz_path, extract_dir)

        # Assert extraction directory exists
        assert extract_dir.exists()
        # Verify expected files are present
        assert (extract_dir / "apps/TA-example/local/inputs.conf").exists()
        assert (extract_dir / "system/local/outputs.conf").exists()
        # Verify file contents match
        content = (extract_dir / "apps/TA-example/local/inputs.conf").read_text()
        assert "[monitor://var/log]" in content
        assert len(extracted_files) == 2

    def test_extract_archive_nested_dirs(self, tmp_path: Path, temp_storage_root: Path):
        """Verify nested directory structure is preserved."""
        # Create archive with nested structure
        zip_path = tmp_path / "nested.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("apps/TA-example/local/inputs.conf", "[monitor://var/log]\n")
            zf.writestr("apps/TA-example/default/inputs.conf", "[default:monitor]\n")
            zf.writestr("system/local/outputs.conf", "[tcpout]\n")
            zf.writestr("system/default/outputs.conf", "[default:tcpout]\n")

        # Extract archive
        extract_dir = temp_storage_root / "extract"
        extracted_files = extract_archive_safe(zip_path, extract_dir)

        # Assert all nested directories are created correctly
        assert (extract_dir / "apps/TA-example/local").exists()
        assert (extract_dir / "apps/TA-example/default").exists()
        assert (extract_dir / "system/local").exists()
        assert (extract_dir / "system/default").exists()

        # Files are in correct locations
        assert (extract_dir / "apps/TA-example/local/inputs.conf").exists()
        assert (extract_dir / "apps/TA-example/default/inputs.conf").exists()

        # Directory structure matches archive
        assert len(extracted_files) == 4

    def test_extract_archive_path_traversal_blocked(self, tmp_path: Path, temp_storage_root: Path):
        """Verify path traversal attacks are prevented."""
        # Create malicious .zip with path traversal
        malicious_zip = tmp_path / "malicious.zip"
        with zipfile.ZipFile(malicious_zip, "w") as zf:
            # Attempt to write to parent directories
            zf.writestr("../../../etc/passwd", "malicious content")

        # Attempt extraction
        extract_dir = temp_storage_root / "extract"
        with pytest.raises(ValueError, match="Path traversal attempt"):
            extract_archive_safe(malicious_zip, extract_dir)

        # Verify no files extracted outside target
        # The extract_dir might not even exist if error raised before any extraction
        if extract_dir.exists():
            # Check that no files were created in parent dirs
            assert not (tmp_path / "etc").exists()
            assert not (tmp_path.parent / "etc").exists()

    def test_extract_tar_path_traversal_blocked(self, tmp_path: Path, temp_storage_root: Path):
        """Verify TAR path traversal attacks are prevented."""
        # Create malicious .tar.gz with path traversal
        malicious_tar = tmp_path / "malicious.tar.gz"
        with tarfile.open(malicious_tar, "w:gz") as tf:
            # Construct member with path traversal
            member = tarfile.TarInfo(name="../../etc/passwd")
            member.size = len(b"x")
            tf.addfile(member, io.BytesIO(b"x"))

        # Attempt extraction
        extract_dir = temp_storage_root / "extract"
        with pytest.raises(ValueError, match="Path traversal attempt"):
            extract_archive_safe(malicious_tar, extract_dir)

        # Verify no files were created outside target
        assert not (tmp_path / "etc").exists()

    def test_extract_archive_tgz(self, tmp_path: Path, temp_storage_root: Path):
        """Extract .tgz archive, verify directory structure."""
        # Create a .tgz file with a simple conf file
        tgz_path = tmp_path / "test.tgz"
        with tarfile.open(tgz_path, "w:gz") as tf:
            conf_data = b"[monitor://var/log]\nindex=main\n"
            conf_info = tarfile.TarInfo(name="inputs.conf")
            conf_info.size = len(conf_data)
            tf.addfile(conf_info, io.BytesIO(conf_data))

        # Extract archive
        extract_dir = temp_storage_root / "extract_tgz"
        extracted_files = extract_archive_safe(tgz_path, extract_dir)

        # Assert extraction directory exists
        assert extract_dir.exists()
        # Verify expected file is present
        assert (extract_dir / "inputs.conf").exists()
        # Verify file contents match
        content = (extract_dir / "inputs.conf").read_text()
        assert "[monitor://var/log]" in content
        assert len(extracted_files) == 1

    def test_extract_archive_tar(self, tmp_path: Path, temp_storage_root: Path):
        """Extract plain .tar archive, verify directory structure."""
        # Create a plain .tar file with a simple conf file
        tar_path = tmp_path / "test.tar"
        with tarfile.open(tar_path, "w") as tf:
            conf_data = b"[tcpout]\ndefaultGroup=indexers\n"
            conf_info = tarfile.TarInfo(name="outputs.conf")
            conf_info.size = len(conf_data)
            tf.addfile(conf_info, io.BytesIO(conf_data))

        # Extract archive
        extract_dir = temp_storage_root / "extract_tar"
        extracted_files = extract_archive_safe(tar_path, extract_dir)

        # Assert extraction directory exists
        assert extract_dir.exists()
        # Verify expected file is present
        assert (extract_dir / "outputs.conf").exists()
        # Verify file contents match
        content = (extract_dir / "outputs.conf").read_text()
        assert "[tcpout]" in content
        assert len(extracted_files) == 1

    def test_extract_unsupported_extension(self, tmp_path: Path, temp_storage_root: Path):
        """Verify unsupported archive extension raises ValueError."""
        # Create a dummy file with unsupported extension
        dummy_path = tmp_path / "dummy.bin"
        dummy_path.write_bytes(b"\x00\x01\x02\x03\x04\x05")

        # Attempt extraction
        extract_dir = temp_storage_root / "extract"
        with pytest.raises(ValueError, match="Unsupported archive format"):
            extract_archive_safe(dummy_path, extract_dir)


@pytest.mark.unit
class TestFileValidation:
    """Test file type validation."""

    def test_validate_file_extension_zip(self):
        """Verify .zip extension is accepted."""
        assert validate_file_extension("file.zip") is True

    def test_validate_file_extension_tar_gz(self):
        """Verify .tar.gz extension is accepted."""
        assert validate_file_extension("file.tar.gz") is True

    def test_validate_file_extension_tgz(self):
        """Verify .tgz extension is accepted."""
        assert validate_file_extension("file.tgz") is True

    def test_validate_file_extension_invalid(self):
        """Reject invalid file extensions."""
        assert validate_file_extension("file.exe") is False
        assert validate_file_extension("file.txt") is False
        assert validate_file_extension("file.pdf") is False

    def test_validate_magic_bytes_zip(self, tmp_path: Path):
        """Verify ZIP magic bytes (PK\\x03\\x04)."""
        # Create real .zip file
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.conf", "content")

        # Validate magic bytes
        assert validate_archive_content(zip_path) is True

    def test_validate_magic_bytes_tar_gz(self, tmp_path: Path):
        """Verify gzip magic bytes (\\x1f\\x8b)."""
        # Create real .tar.gz file
        tar_gz_path = tmp_path / "test.tar.gz"
        with tarfile.open(tar_gz_path, "w:gz") as tf:
            info = tarfile.TarInfo(name="test.conf")
            info.size = 7
            tf.addfile(info, io.BytesIO(b"content"))

        # Validate magic bytes
        assert validate_archive_content(tar_gz_path) is True


@pytest.mark.unit
class TestSafePathExtraction:
    """Test path traversal prevention."""

    def test_safe_extract_path_valid(self, tmp_path: Path):
        """Allow valid relative paths."""
        # Test valid path within base
        valid_path = tmp_path / "apps/TA-example/local/inputs.conf"
        assert validate_path_safety(tmp_path, valid_path) is True

    def test_safe_extract_path_traversal_attempt(self, tmp_path: Path):
        """Block path traversal with ../."""
        # Create path with traversal
        traversal_path = tmp_path / "../../../etc/passwd"
        # Resolve to see actual path
        resolved = traversal_path.resolve()

        # Should return False (path escapes base directory)
        assert validate_path_safety(tmp_path, resolved) is False

    def test_safe_extract_path_absolute(self, tmp_path: Path):
        """Block absolute paths."""
        # Test absolute path outside base
        absolute_path = Path("/etc/passwd")
        assert validate_path_safety(tmp_path, absolute_path) is False

    @pytest.mark.skipif(sys.platform == "win32", reason="Symlink test requires Unix")
    def test_safe_extract_path_symlink(self, tmp_path: Path, temp_storage_root: Path):
        """Block symlink creation pointing outside extraction directory."""
        # Create a symlink target outside extraction directory
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        target_file = outside_dir / "target.txt"
        target_file.write_text("sensitive data")

        # Create archive with symlink
        zip_path = tmp_path / "symlink.zip"
        extract_dir = temp_storage_root / "extract"

        with zipfile.ZipFile(zip_path, "w") as zf:
            # Add a regular file
            zf.writestr("normal.conf", "content")

            # Create a ZipInfo for symlink (Unix systems)
            # Note: Creating actual symlink in ZIP requires special handling
            # For this test, we verify that extract_archive_safe filters symlinks
            symlink_info = zipfile.ZipInfo("malicious_link")
            # Mark as symlink using Unix external attribute (S_IFLNK << 16).
            # See: https://github.com/python/cpython/issues/88102
            symlink_info.external_attr = 0xA0000000  # S_IFLNK << 16 for symlink
            zf.writestr(symlink_info, "../outside/target.txt")

        # Extract - should filter out symlinks
        extracted_files = extract_archive_safe(zip_path, extract_dir)

        # Verify symlink was filtered (not in extracted files)
        assert not any("malicious_link" in str(f) for f in extracted_files)
        # Verify only regular file was extracted
        assert (extract_dir / "normal.conf").exists()
        assert not (extract_dir / "malicious_link").exists()


@pytest.mark.unit
class TestUploadSaving:
    """Test upload file storage."""

    async def test_save_upload_create_directory(self, temp_storage_root: Path):
        """Verify upload directory is created."""
        # Create mock UploadFile
        mock_file = Mock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=b"")
        mock_file.filename = "test.zip"

        # Save upload
        file_path, size = await save_upload_file(
            upload_id=1, file=mock_file, original_filename="test.zip", max_bytes=1000000
        )

        # Assert directory exists
        assert (temp_storage_root / "artifacts/1").exists()
        # Verify function returns tuple
        assert isinstance(file_path, Path)
        assert isinstance(size, int)

    async def test_save_upload_file_stored(self, temp_storage_root: Path):
        """Verify uploaded file is saved correctly."""
        # Create test data with ZIP magic bytes
        test_data = b"PK\x03\x04" + b"test content" * 100

        # Create mock that returns data in chunks
        mock_file = Mock(spec=UploadFile)
        chunks = [test_data[i : i + CHUNK_SIZE] for i in range(0, len(test_data), CHUNK_SIZE)]
        mock_file.read = AsyncMock(side_effect=chunks + [b""])  # Empty bytes signals EOF
        mock_file.filename = "test.zip"

        # Save upload
        file_path, file_size = await save_upload_file(
            upload_id=1, file=mock_file, original_filename="test.zip", max_bytes=1000000
        )

        # Assert file exists
        assert file_path.exists()
        # Verify file size matches
        assert file_size == len(test_data)
        # Verify file contents match
        assert file_path.read_bytes() == test_data
        # Verify chunked reading: mock_file.read called once per chunk plus one for EOF
        assert mock_file.read.call_count == len(chunks) + 1

    async def test_save_upload_duplicate_overwrites(self, temp_storage_root: Path):
        """Verify that saving with same upload_id overwrites previous file."""
        # First upload
        mock_file1 = Mock(spec=UploadFile)
        mock_file1.read = AsyncMock(side_effect=[b"first content", b""])
        mock_file1.filename = "test1.zip"

        file_path1, size1 = await save_upload_file(
            upload_id=1, file=mock_file1, original_filename="test1.zip", max_bytes=1000000
        )

        # Second upload with same ID
        mock_file2 = Mock(spec=UploadFile)
        mock_file2.read = AsyncMock(side_effect=[b"second content overwrite", b""])
        mock_file2.filename = "test2.zip"

        file_path2, size2 = await save_upload_file(
            upload_id=1, file=mock_file2, original_filename="test2.zip", max_bytes=1000000
        )

        # Verify second save overwrites
        assert file_path2.exists()
        assert file_path2.read_bytes() == b"second content overwrite"
        assert size2 == len(b"second content overwrite")

    async def test_save_upload_size_limit_exceeded(self, temp_storage_root: Path):
        """Verify size limit enforcement and partial file cleanup."""
        # Create mock UploadFile
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "too_big.zip"

        # Prepare chunks that will exceed the limit
        chunk_ok = b"A" * (CHUNK_SIZE // 2)
        chunk_over = b"B" * (CHUNK_SIZE // 2)
        mock_file.read = AsyncMock(side_effect=[chunk_ok, chunk_over, b""])

        # Attempt to save with size limit that will be exceeded
        with pytest.raises(ValueError, match="File size exceeds maximum"):
            await save_upload_file(
                upload_id=1,
                file=mock_file,
                original_filename="too_big.zip",
                max_bytes=len(chunk_ok),
            )
        assert not (temp_storage_root / "artifacts/1/upload.zip").exists()
        # Verify partial file was cleaned up
        assert not (temp_storage_root / "artifacts/1/upload.zip").exists()

    async def test_save_upload_read_error_cleanup(self, temp_storage_root: Path):
        """Validate cleanup on generic I/O error during upload streaming."""
        # Create mock UploadFile that raises exception during read
        mock_file = Mock(spec=UploadFile)
        mock_file.read = AsyncMock(side_effect=[b"chunk", Exception("boom")])
        mock_file.filename = "ioerr.zip"

        # Attempt to save - should raise the exception
        with pytest.raises(Exception, match="boom"):
            await save_upload_file(
                upload_id=1,
                file=mock_file,
                original_filename="ioerr.zip",
                max_bytes=10**6,
            )

        # Verify partial file was cleaned up
        assert (temp_storage_root / "artifacts/1/upload.zip").exists() is False


@pytest.mark.unit
class TestParsedConfigStorage:
    """Test parsed config storage.

    NOTE: These functions (store_parsed_config, store_canonical_graph) do not exist
    in storage.py because the processor stores data directly in the database
    (Graph.json_blob), not as separate files.
    """

    @pytest.mark.skip(
        reason="store_parsed_config not implemented - parsed config not persisted to disk"
    )
    def test_store_parsed_config_json(self, tmp_path: Path, temp_storage_root: Path):
        """Store ParsedConfig as JSON in work directory.

        Skipped: Parsed config is used in-memory during processing and stored
        in the database, not as separate files on disk.
        """
        pass

    @pytest.mark.skip(reason="store_parsed_config not implemented - data stored in database")
    def test_store_parsed_config_nested_structure(self, tmp_path: Path, temp_storage_root: Path):
        """Verify complex nested data structures serialize correctly.

        Skipped: Parsed config is stored in the database as part of processing.
        """
        pass


@pytest.mark.unit
class TestCanonicalGraphStorage:
    """Test canonical graph storage.

    NOTE: These functions do not exist in storage.py because graphs are stored
    in the database Graph.json_blob field, not as separate files.
    """

    @pytest.mark.skip(
        reason="store_canonical_graph not implemented - graph stored in database Graph.json_blob"
    )
    def test_store_canonical_graph_json(self, tmp_path: Path, temp_storage_root: Path):
        """Store canonical graph as JSON.

        Skipped: Canonical graphs are stored in the database Graph.json_blob field,
        not as separate files on disk.
        """
        pass

    @pytest.mark.skip(reason="store_canonical_graph not implemented - data stored in database")
    def test_store_canonical_graph_compression(self, tmp_path: Path, temp_storage_root: Path):
        """Verify large graphs are stored efficiently.

        Skipped: Graph storage and compression is handled by the database.
        """
        pass


@pytest.mark.unit
class TestArtifactCleanup:
    """Test cleanup of job artifacts."""

    def test_cleanup_work_directory(self, temp_storage_root: Path):
        """Remove work directory for a job."""
        # Create work directory with files
        work_dir = get_work_directory(job_id=1)
        (work_dir / "parsed_config.json").write_text('{"test": "data"}')
        (work_dir / "temp_file.txt").write_text("temporary")

        # Verify files exist
        assert work_dir.exists()
        assert (work_dir / "parsed_config.json").exists()

        # Cleanup
        cleanup_work(job_id=1)

        # Assert work directory is deleted
        assert not work_dir.exists()
        # Parent directories still exist
        assert (temp_storage_root / "work").exists()

    def test_cleanup_upload_directory(self, temp_storage_root: Path):
        """Remove upload directory and its contents."""
        # Create upload directory with files
        upload_dir = get_upload_directory(upload_id=1)
        (upload_dir / "upload.zip").write_bytes(b"PK\x03\x04test")
        (upload_dir / "extracted").mkdir()

        # Create another upload directory
        upload_dir2 = get_upload_directory(upload_id=2)
        (upload_dir2 / "upload.tar.gz").write_bytes(b"\x1f\x8btest")

        # Cleanup first upload
        cleanup_upload(upload_id=1)

        # Assert first upload directory is deleted
        assert not upload_dir.exists()
        # Other upload directories are not affected
        assert upload_dir2.exists()

    def test_cleanup_nonexistent_directory(self, temp_storage_root: Path):
        """Handle cleanup of non-existent job gracefully."""
        # Call cleanup for non-existent job
        # Should not raise exception (idempotent)
        cleanup_work(job_id=999)

        # Call again - still should not raise
        cleanup_work(job_id=999)


@pytest.mark.unit
class TestListExtractedFiles:
    """Test listing extracted configuration files.

    NOTE: The function list_extracted_files does not exist in storage.py.
    The parser service uses find_conf_files to discover configuration files.
    """

    @pytest.mark.skip(
        reason="list_extracted_files not implemented - use parser.find_conf_files instead"
    )
    def test_list_extracted_files_all_conf(self, tmp_path: Path):
        """List all .conf files in extracted directory.

        Skipped: The parser service handles .conf file discovery via find_conf_files.
        """
        pass

    @pytest.mark.skip(reason="list_extracted_files not implemented - see parser.find_conf_files")
    def test_list_extracted_files_precedence_order(self, tmp_path: Path):
        """Verify files are returned in precedence order.

        Skipped: File discovery and precedence ordering is handled by the parser.
        """
        pass

    @pytest.mark.skip(reason="list_extracted_files not implemented - see parser.find_conf_files")
    def test_list_extracted_files_empty_directory(self, tmp_path: Path):
        """Handle directory with no .conf files.

        Skipped: File listing is handled by the parser service.
        """
        pass


@pytest.mark.unit
class TestDirectoryManagement:
    """Test directory getter functions and management."""

    def test_get_storage_root(self, temp_storage_root: Path):
        """Verify get_storage_root returns valid path."""
        storage_root = get_storage_root()
        assert isinstance(storage_root, Path)
        assert storage_root.exists()
        assert storage_root.is_dir()

    def test_get_upload_directory(self, temp_storage_root: Path):
        """Verify upload directory creation."""
        upload_dir = get_upload_directory(upload_id=1)

        # Returns Path object
        assert isinstance(upload_dir, Path)
        # Directory exists
        assert upload_dir.exists()
        # Path matches pattern {storage_root}/artifacts/1
        assert upload_dir == temp_storage_root / "artifacts/1"

    def test_get_work_directory(self, temp_storage_root: Path):
        """Verify work directory creation."""
        work_dir = get_work_directory(job_id=1)

        # Returns Path object
        assert isinstance(work_dir, Path)
        # Directory exists
        assert work_dir.exists()
        # Path matches pattern {storage_root}/work/1
        assert work_dir == temp_storage_root / "work/1"

    def test_ensure_directory_creates_nested(self, temp_storage_root: Path):
        """Verify ensure_directory creates nested directories."""
        nested_path = temp_storage_root / "a/b/c/d"
        result = ensure_directory(nested_path)

        # All nested directories are created
        assert nested_path.exists()
        assert (temp_storage_root / "a").exists()
        assert (temp_storage_root / "a/b").exists()
        assert (temp_storage_root / "a/b/c").exists()
        # Returns the created path
        assert result == nested_path

    def test_ensure_directory_outside_storage_root(self, temp_storage_root: Path):
        """Verify ensure_directory rejects paths outside storage root."""
        # Attempt to create directory outside storage root
        malicious_path = Path("/etc/malicious")

        with pytest.raises(ValueError, match="outside storage root"):
            ensure_directory(malicious_path)

    def test_generate_storage_uri(self, temp_storage_root: Path):
        """Verify storage URI generation."""
        # Test .zip file
        uri_zip = generate_storage_uri(upload_id=1, filename="test.zip")
        assert "/artifacts/1/upload.zip" in uri_zip
        assert isinstance(uri_zip, str)

        # Test .tar.gz file (special handling)
        uri_tar_gz = generate_storage_uri(upload_id=2, filename="test.tar.gz")
        assert "/artifacts/2/upload.tar.gz" in uri_tar_gz

    def test_get_file_size(self, tmp_path: Path):
        """Verify get_file_size returns correct size."""
        # Create test file with known size
        test_file = tmp_path / "test.txt"
        test_content = b"test content" * 100
        test_file.write_bytes(test_content)

        # Get file size
        size = get_file_size(test_file)

        # Assert returned size matches actual
        assert size == len(test_content)
        assert size == test_file.stat().st_size

    def test_get_graphs_directory(self, temp_storage_root: Path):
        """Verify graphs directory creation."""
        graphs_dir = get_graphs_directory()

        assert isinstance(graphs_dir, Path)
        assert graphs_dir.exists()
        assert graphs_dir == temp_storage_root / "graphs"

    def test_get_exports_directory(self, temp_storage_root: Path):
        """Verify exports directory creation."""
        exports_dir = get_exports_directory()

        assert isinstance(exports_dir, Path)
        assert exports_dir.exists()
        assert exports_dir == temp_storage_root / "exports"

    def test_cleanup_directory_recursive(self, temp_storage_root: Path):
        """Verify cleanup_directory removes entire tree."""
        # Create nested directory structure
        test_dir = temp_storage_root / "test_cleanup"
        test_dir.mkdir()
        (test_dir / "sub1").mkdir()
        (test_dir / "sub1/file1.txt").write_text("content")
        (test_dir / "sub2").mkdir()
        (test_dir / "sub2/file2.txt").write_text("content")

        # Cleanup recursively
        cleanup_directory(test_dir, recursive=True)

        # Verify entire tree is deleted
        assert not test_dir.exists()

    def test_cleanup_directory_prevents_storage_root_deletion(self, temp_storage_root: Path):
        """Verify cleanup_directory prevents deletion of storage root."""
        with pytest.raises(ValueError, match="Cannot delete storage root"):
            cleanup_directory(temp_storage_root, recursive=True)

        # Storage root still exists
        assert temp_storage_root.exists()

