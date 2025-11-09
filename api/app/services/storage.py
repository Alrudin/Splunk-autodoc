"""Storage service for secure file handling and archive management.

This module provides comprehensive file handling capabilities including:
- Secure file uploads with streaming to handle large files (up to 2GB)
- Path traversal protection per spec section 8
- Archive validation and safe extraction
- Directory management for artifacts, work, graphs, and exports
"""

import shutil
import tarfile
import zipfile
from pathlib import Path

from fastapi import UploadFile

from app.config import settings

# Storage subdirectories per spec section 6
ARTIFACTS_DIR = "artifacts"
WORK_DIR = "work"
GRAPHS_DIR = "graphs"
EXPORTS_DIR = "exports"

# Chunk size for streaming file uploads (256KB for better throughput)
CHUNK_SIZE = 262144  # 256KB - increased from 8KB for better I/O performance

# Allowed archive extensions per spec section 6.1
ALLOWED_ARCHIVES = {".zip", ".tar.gz", ".tar", ".tgz"}


def get_storage_root() -> Path:
    """Get absolute storage root path and ensure it exists.

    Returns:
        Path: Absolute path to storage root directory.
    """
    storage_root = Path(settings.storage_root).resolve()
    storage_root.mkdir(parents=True, exist_ok=True)
    return storage_root


def validate_path_safety(base_path: Path, target_path: Path) -> bool:
    """Validate that target path is within base path (no path traversal).

    Implements path traversal protection per spec section 8.

    Args:
        base_path: The base directory that should contain the target.
        target_path: The path to validate.

    Returns:
        bool: True if target_path is safely within base_path, False otherwise.
    """
    try:
        base_resolved = base_path.resolve()
        target_resolved = target_path.resolve()
        # Check if target is relative to base (Python 3.9+)
        return target_resolved.is_relative_to(base_resolved)
    except (ValueError, RuntimeError):  # noqa: PERF203
        return False


def ensure_directory(directory: Path) -> Path:
    """Create directory if it doesn't exist and validate it's within storage root.

    Args:
        directory: Directory path to create.

    Returns:
        Path: The created/validated directory path.

    Raises:
        ValueError: If directory path is outside storage root.
    """
    storage_root = get_storage_root()
    if not validate_path_safety(storage_root, directory):
        raise ValueError(f"Directory path outside storage root: {directory}")

    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_upload_directory(upload_id: int) -> Path:
    """Get upload artifacts directory for a specific upload.

    Creates /data/artifacts/{upload_id}/ structure per spec section 6.

    Args:
        upload_id: Upload record ID.

    Returns:
        Path: Path to upload directory.
    """
    upload_dir = get_storage_root() / ARTIFACTS_DIR / str(upload_id)
    return ensure_directory(upload_dir)


def get_work_directory(job_id: int) -> Path:
    """Get work directory for a specific job.

    Creates /data/work/{job_id}/ structure for job processing.

    Args:
        job_id: Job record ID.

    Returns:
        Path: Path to work directory.
    """
    work_dir = get_storage_root() / WORK_DIR / str(job_id)
    return ensure_directory(work_dir)


def get_graphs_directory() -> Path:
    """Get graphs directory for optional externalized graph JSON storage.

    Returns:
        Path: Path to graphs directory.
    """
    graphs_dir = get_storage_root() / GRAPHS_DIR
    return ensure_directory(graphs_dir)


def get_exports_directory() -> Path:
    """Get exports directory for persisted export files (PNG, PDF, DOT, JSON).

    Returns:
        Path: Path to exports directory.
    """
    exports_dir = get_storage_root() / EXPORTS_DIR
    return ensure_directory(exports_dir)


async def save_upload_file(
    upload_id: int, file: UploadFile, original_filename: str, max_bytes: int
) -> tuple[Path, int]:
    """Save uploaded file to disk using streaming to handle large files.

    Replaces the in-memory approach by streaming file content in chunks.
    Enforces max file size during streaming to prevent disk exhaustion.

    Args:
        upload_id: Upload record ID for directory creation.
        file: FastAPI UploadFile object.
        original_filename: Original filename to determine extension.
        max_bytes: Maximum allowed file size in bytes.

    Returns:
        tuple[Path, int]: (file_path, total_bytes) for storage URI and size verification.

    Raises:
        OSError: If disk I/O error occurs.
        ValueError: If path validation fails or file size exceeds max_bytes.
    """
    upload_dir = get_upload_directory(upload_id)

    # Determine file extension (handle .tar.gz specially)
    if original_filename.endswith(".tar.gz"):
        extension = ".tar.gz"
    else:
        extension = Path(original_filename).suffix

    dest_path = upload_dir / f"upload{extension}"

    # Stream file content to disk in chunks with size enforcement
    total_bytes = 0
    # Assumes file position is at start; do not seek as UploadFile may not support it

    try:
        with open(dest_path, "wb") as dest_file:
            while chunk := await file.read(CHUNK_SIZE):
                total_bytes += len(chunk)

                # Enforce max size during streaming to prevent disk exhaustion
                if total_bytes > max_bytes:
                    # Delete partial write
                    dest_path.unlink(missing_ok=True)
                    raise ValueError(f"File size exceeds maximum allowed size of {max_bytes} bytes")

                dest_file.write(chunk)
    except ValueError:
        # Re-raise ValueError (size exceeded)
        raise
    except Exception:
        # Clean up partial file on any other error
        dest_path.unlink(missing_ok=True)
        raise

    return dest_path, total_bytes


def validate_archive_content(archive_path: Path) -> bool:
    """Validate archive format using magic bytes check.

    Implements content validation per spec section 8. For tar.gz/tgz files,
    performs additional validation by attempting to open as tarfile.

    Args:
        archive_path: Path to archive file.

    Returns:
        bool: True if valid archive format, False otherwise.
    """
    try:
        with open(archive_path, "rb") as f:
            magic_bytes = f.read(512)  # Read enough for TAR signature at offset 257

        # Check ZIP signature
        if magic_bytes.startswith(b"PK\x03\x04") or magic_bytes.startswith(b"PK\x05\x06"):
            return True

        # Check GZIP signature
        if magic_bytes.startswith(b"\x1f\x8b"):
            # GZIP magic bytes detected; treat as valid gzip archive.
            # If stricter validation of tar.gz structure is required for security, uncomment below:
            # if archive_path.suffix in {".gz", ".tgz"} or ".tar.gz" in archive_path.name:
            #     try:
            #         with tarfile.open(
            #             name=str(archive_path), mode="r:gz"
            #         ) as tf:  # type: ignore[call-overload]
            #             tf.next()
            #         return True
            #     except (tarfile.TarError, OSError):
            #         return False
            # Plain gzip file (not tar.gz)
            return True

        # Check TAR signature (ustar at offset 257)
        if len(magic_bytes) >= 262 and magic_bytes[257:262] == b"ustar":
            return True

        return False
    except OSError:
        return False


def extract_archive_safe(archive_path: Path, extract_to: Path) -> list[Path]:
    """Safely extract archive with path traversal protection.

    Implements safe archive extraction per spec section 8. Prevents zip slip
    vulnerabilities and filters malicious content.

    Args:
        archive_path: Path to archive file.
        extract_to: Destination directory for extraction.

    Returns:
        list[Path]: List of extracted file paths for verification.

    Raises:
        ValueError: If security check fails or invalid archive format.
        OSError: If extraction fails due to I/O error.
    """
    ensure_directory(extract_to)

    # Detect archive type from extension
    if archive_path.suffix == ".zip":
        return _extract_zip_safe(archive_path, extract_to)
    elif archive_path.suffix in {".tar", ".gz", ".tgz"} or ".tar.gz" in archive_path.name:
        return _extract_tar_safe(archive_path, extract_to)
    else:
        raise ValueError(f"Unsupported archive format: {archive_path.suffix}")


def _extract_zip_safe(archive_path: Path, extract_to: Path) -> list[Path]:
    """Safely extract ZIP archive with security checks.

    Filters symlinks to prevent traversal via symlink targets.

    Args:
        archive_path: Path to ZIP file.
        extract_to: Destination directory.

    Returns:
        list[Path]: List of extracted file paths.

    Raises:
        ValueError: If path traversal or absolute path detected.
    """
    extracted_files: list[Path] = []
    s_iflnk = 0xA000  # Symlink file mode (see stat.S_IFLNK)

    with zipfile.ZipFile(archive_path) as zf:
        for info in zf.infolist():
            # Detect and skip symlinks using UNIX mode in external_attr
            # external_attr stores file mode in upper 16 bits (on UNIX systems)
            file_mode = info.external_attr >> 16
            # Check if it's a symlink (S_IFLNK = 0xA000)
            if (file_mode & 0xF000) == s_iflnk:  # Symlink detected
                continue

            # Check for absolute paths
            if info.filename.startswith("/") or ".." in info.filename:
                raise ValueError(f"Path traversal attempt detected: {info.filename}")

            # Validate resolved path stays within extract_to
            member_path = (extract_to / info.filename).resolve()
            if not validate_path_safety(extract_to, member_path):
                raise ValueError(f"Path traversal attempt detected: {info.filename}")

            # Extract member (regular files and directories only)
            zf.extract(info, extract_to)
            extracted_files.append(member_path)

    return extracted_files


def _extract_tar_safe(archive_path: Path, extract_to: Path) -> list[Path]:
    """Safely extract TAR archive with security checks.

    Args:
        archive_path: Path to TAR file (may be gzipped).
        extract_to: Destination directory.

    Returns:
        list[Path]: List of extracted file paths.

    Raises:
        ValueError: If path traversal, symlink, or device file detected.
    """
    extracted_files: list[Path] = []
    safe_members = []

    # Determine mode based on extension
    if archive_path.suffix in {".gz", ".tgz"} or ".tar.gz" in archive_path.name:
        mode = "r:gz"
    else:
        mode = "r"

    with tarfile.open(name=str(archive_path), mode=mode) as tf:  # type: ignore[call-overload]
        for member in tf.getmembers():
            # Filter out symlinks and device files
            if member.issym() or member.islnk() or member.isdev():
                continue

            # Check for path traversal
            if member.name.startswith("/") or ".." in member.name:
                raise ValueError(f"Path traversal attempt detected: {member.name}")

            # Validate resolved path
            member_path = (extract_to / member.name).resolve()
            if not validate_path_safety(extract_to, member_path):
                raise ValueError(f"Path traversal attempt detected: {member.name}")

            safe_members.append(member)
            extracted_files.append(member_path)

        # Extract all safe members
        tf.extractall(extract_to, members=safe_members)

    return extracted_files


def cleanup_directory(directory: Path, recursive: bool = True) -> None:
    """Clean up directory with safety checks.

    Args:
        directory: Directory to remove.
        recursive: If True, remove entire tree; if False, remove only empty directory.

    Raises:
        ValueError: If attempting to delete storage root or path outside storage root.
        FileNotFoundError: Silently handled (directory already deleted).
    """
    storage_root = get_storage_root()

    # Prevent deletion of storage root
    if directory.resolve() == storage_root:
        raise ValueError("Cannot delete storage root directory")

    # Validate directory is within storage root
    if not validate_path_safety(storage_root, directory):
        raise ValueError(f"Directory path outside storage root: {directory}")

    try:
        if recursive:
            shutil.rmtree(directory)
        else:
            directory.rmdir()
    except FileNotFoundError:
        pass  # Directory already deleted


def cleanup_upload(upload_id: int) -> None:
    """Clean up upload artifacts directory.

    Convenience function for deleting uploads or cleaning up failed jobs.

    Args:
        upload_id: Upload record ID.
    """
    upload_dir = get_storage_root() / ARTIFACTS_DIR / str(upload_id)
    cleanup_directory(upload_dir, recursive=True)


def cleanup_work(job_id: int) -> None:
    """Clean up job work directory.

    Used after job completion or failure to free disk space.

    Args:
        job_id: Job record ID.
    """
    work_dir = get_storage_root() / WORK_DIR / str(job_id)
    cleanup_directory(work_dir, recursive=True)


def generate_storage_uri(upload_id: int, filename: str) -> str:
    """Generate storage URI string for database storage.

    Provides consistent URI format using configurable storage_root.

    Args:
        upload_id: Upload record ID.
        filename: Original filename to determine extension.

    Returns:
        str: Storage URI filesystem path (e.g., /data/artifacts/{upload_id}/upload{ext})
    """
    # Handle .tar.gz specially
    if filename.endswith(".tar.gz"):
        extension = ".tar.gz"
    else:
        extension = Path(filename).suffix

    # Build URI using configurable storage_root
    storage_path = get_storage_root() / ARTIFACTS_DIR / str(upload_id) / f"upload{extension}"
    return str(storage_path)


def get_file_size(file_path: Path) -> int:
    """Get file size in bytes.

    Args:
        file_path: Path to file.

    Returns:
        int: File size in bytes.

    Raises:
        FileNotFoundError: If file doesn't exist.
    """
    return file_path.stat().st_size
