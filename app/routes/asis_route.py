from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth_middleware import admin_only
from app.schemas.asis_schema import AsisApplyRequest
from app.services import asis_sync_service

router = APIRouter(prefix="/asis", tags=["ASIS"])


@router.post("/sync", dependencies=[Depends(admin_only)])
def sync_asis(db: Session = Depends(get_db)):
    return asis_sync_service.sync_all(db)


@router.get("/preview", dependencies=[Depends(admin_only)])
def preview_asis(db: Session = Depends(get_db)):
    return asis_sync_service.preview(db)


@router.post("/apply", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)])
def apply_asis(data: AsisApplyRequest, db: Session = Depends(get_db)):
    if not data.company_ids and not data.branch_ids and data.category_ids == []:
        raise HTTPException(status_code=400, detail="Tidak ada data yang dipilih")
    try:
        asis_sync_service.apply_selected(db, data.company_ids, data.branch_ids, data.category_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
