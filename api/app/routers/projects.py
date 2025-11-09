
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db  # type: ignore
from app.models.project import Project  # type: ignore
from app.schemas import ProjectCreate, ProjectResponse, ProjectUpdate  # type: ignore

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ProjectResponse)
def create_project(project_data: ProjectCreate, db: Session = Depends(get_db)) -> ProjectResponse:  # noqa: B008
    """
    Create a new project.

    Args:
        project_data: Project creation data (name, labels)
        db: Database session

    Returns:
        Created project with generated ID and timestamps
    """
    try:
        project = Project(name=project_data.name, labels=project_data.labels)
        db.add(project)
        db.commit()
        db.refresh(project)
        return project
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Database integrity error: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}",
        )


class ProjectListResponse(BaseModel):
    id: int
    name: str
    labels: dict | None = None
    created_at: str | None = None
    updated_at: str | None = None

    class Config:
        orm_mode = True

@router.get("/", response_model=list[ProjectListResponse])
def list_projects(db: Session = Depends(get_db)) -> list[ProjectListResponse]:  # noqa: B008
    """
    List all projects ordered by creation date (newest first).

    Args:
        db: Database session

    Returns:
        List of all projects
    """
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return projects


@router.get("/{id}", response_model=ProjectResponse)
def get_project(id: int, db: Session = Depends(get_db)) -> ProjectResponse:  # noqa: B008
    """
    Get a single project by ID.

    Args:
        id: Project ID
        db: Database session

    Returns:
        Project with the specified ID

    Raises:
        HTTPException: 404 if project not found
    """
    project = db.query(Project).filter(Project.id == id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.patch("/{id}", response_model=ProjectResponse)
def update_project(
    id: int, project_data: ProjectUpdate, db: Session = Depends(get_db)  # noqa: B008
) -> ProjectResponse:
    """
    Update a project's name and/or labels.

    Args:
        id: Project ID
        project_data: Fields to update
        db: Database session

    Returns:
        Updated project

    Raises:
        HTTPException: 404 if project not found
    """
    project = db.query(Project).filter(Project.id == id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    try:
        # Update only provided fields
        if project_data.name is not None:
            project.name = project_data.name
        if project_data.labels is not None:
            project.labels = project_data.labels

        db.commit()
        db.refresh(project)
        return project
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Database integrity error: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}",
        )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(id: int, db: Session = Depends(get_db)) -> Response:  # noqa: B008
    """
    Delete a project and all related uploads and graphs (cascade).

    Args:
        id: Project ID
        db: Database session

    Returns:
        No content (204)

    Raises:
        HTTPException: 404 if project not found
    """
    project = db.query(Project).filter(Project.id == id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    try:
        db.delete(project)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        db.rollback()
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}",
        )
