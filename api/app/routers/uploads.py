from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db  # type: ignore
from app.models.project import Project  # type: ignore
from app.models.upload import Upload  # type: ignore
from app.schemas import UploadResponse  # type: ignore

router = APIRouter(tags=["uploads"])

# Allowed file extensions per spec section 8
ALLOWED_EXTENSIONS = {".zip", ".tar.gz", ".tar", ".tgz"}
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB per spec section 13


def validate_file_extension(filename: str) -> bool:
    """
    Validate that the file has an allowed extension.

    Args:
        filename: Name of the uploaded file

    Returns:
        True if extension is allowed
    """
    filename_lower = filename.lower()
    for ext in ALLOWED_EXTENSIONS:
        if filename_lower.endswith(ext):
            return True
    return False


@router.post(
    "/projects/{project_id}/uploads",
    status_code=status.HTTP_201_CREATED,
    response_model=UploadResponse,
)
async def create_upload(
    project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)  # noqa: B008
) -> UploadResponse:
    """
    Create a new upload for a project.

    Args:
        project_id: ID of the project to upload to
        file: Uploaded file (multipart/form-data)
        db: Database session

    Returns:
        Created upload record with pending status

    Raises:
        HTTPException: 404 if project not found, 400 if file validation fails
    """
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided")

    if not validate_file_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file to get size (in production, this should stream to disk)
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024**3):.1f}GB",
        )

    # Create placeholder storage URI (actual file saving handled by storage service)
    # Format: /data/artifacts/pending/{filename}
    storage_uri = f"/data/artifacts/pending/{file.filename}"

    try:
        # Create upload record
        upload = Upload(
            project_id=project_id,
            filename=file.filename,
            size=file_size,
            status="pending",
            storage_uri=storage_uri,
        )
        db.add(upload)
        db.commit()
        db.refresh(upload)

        # Note: Actual file saving will be implemented in storage service
        # Storage service will:
        # - Create directory structure /data/artifacts/{upload_id}/
        # - Save uploaded file securely
        # - Update storage_uri with actual path
        # - Validate file content (magic bytes, safe extraction)

        return upload
    except Exception as e:
        db.rollback()
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create upload: {str(e)}",
        )


@router.get("/uploads/{upload_id}", response_model=UploadResponse)
def get_upload(upload_id: int, db: Session = Depends(get_db)) -> UploadResponse:  # noqa: B008
    """
    Get upload details by ID.

    Args:
        upload_id: Upload ID
        db: Database session

    Returns:
        Upload with related project and jobs

    Raises:
        HTTPException: 404 if upload not found
    """
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    return upload
