from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth_middleware import admin_only
from app.services import asis_sync_service

router = APIRouter(prefix="/asis", tags=["ASIS"])


@router.post("/sync", dependencies=[Depends(admin_only)])
def sync_asis(db: Session = Depends(get_db)):
    return asis_sync_service.sync_all(db)
