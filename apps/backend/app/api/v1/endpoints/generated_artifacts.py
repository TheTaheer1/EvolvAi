from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.generated_artifact import GeneratedArtifactRead
from app.services.generated_artifact_service import GeneratedArtifactService

router = APIRouter()


@router.get("/generated-artifacts/{artifact_id}", response_model=GeneratedArtifactRead)
def get_generated_artifact(artifact_id: UUID, db: Session = Depends(get_db)):
    return GeneratedArtifactService().get_artifact(db, artifact_id)
