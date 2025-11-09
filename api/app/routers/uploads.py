from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db  # type: ignore
from app.models.project import Project  # type: ignore
from app.models.upload import Upload  # type: ignore
from app.schemas import UploadResponse  # type: ignore
from app.services import storage

router = APIRouter(tags=["uploads"])

# Allowed file extensions per spec section 8
ALLOWED_EXTENSIONS = {".zip", ".tar.gz", ".tar", ".tgz"}
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB per spec section 13

# Sentinel value for storage_uri before file is saved
STORAGE_URI_PENDING = "__PENDING__"


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
    project_id: int,
    file: UploadFile = File(...),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> UploadResponse:
    """
    Create a new upload for a project.

    Args:
        project_id: ID of the project to upload to
        file: Uploaded file (multipart/form-data)
        db: Database session

    Returns:
        Created upload record with completed status and actual storage location

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

    # Step 1: Create upload record first (to get upload_id for directory creation)
    upload = Upload(
        project_id=project_id,
        filename=file.filename,
        size=0,  # Will be updated after file save
        status="pending",
        storage_uri=STORAGE_URI_PENDING,  # Will be updated after file save
    )
    try:
        db.add(upload)
        db.commit()
        db.refresh(upload)
    except Exception as e:
        db.rollback()
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create upload record: {str(e)}",
        )

    # Step 2: Save file using storage service (streaming with size enforcement)
    try:
        file_path, file_size = await storage.save_upload_file(
            upload.id, file, file.filename, MAX_FILE_SIZE
        )
    except ValueError as e:
        # Size limit exceeded during streaming
        storage.cleanup_upload(upload.id)
        db.delete(upload)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        # Clean up database record on storage error
        db.delete(upload)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        ) from e

    # Step 3: Validate archive content (magic bytes check)
    if not storage.validate_archive_content(file_path):
        # Clean up saved file and database record
        storage.cleanup_upload(upload.id)
        db.delete(upload)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid archive format",
        )

    # Step 4: Update upload record with actual values
    try:
        storage_uri = storage.generate_storage_uri(upload.id, file.filename)
        upload.size = file_size
        upload.storage_uri = storage_uri
        upload.status = "completed"
        db.commit()
        db.refresh(upload)
        return upload
    except Exception as e:
        # Clean up on database update error
        storage.cleanup_upload(upload.id)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update upload record: {str(e)}",
        ) from e


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
