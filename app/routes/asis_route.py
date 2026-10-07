from fastapi import APIRouter, Depends, status

from app.dependencies import get_asis_sync_service
from app.exceptions import BadRequestError
from app.middleware.auth_middleware import admin_only
from app.schemas.asis_schema import AsisApplyRequest
from app.services.asis_sync_service import AsisSyncService

router = APIRouter(prefix="/asis", tags=["ASIS"])

@router.post("/sync", dependencies=[Depends(admin_only)])
def sync_asis(service: AsisSyncService = Depends(get_asis_sync_service)):
    return service.sync_all()

@router.get("/preview", dependencies=[Depends(admin_only)])
def preview_asis(service: AsisSyncService = Depends(get_asis_sync_service)):
    return service.preview()

@router.post("/apply", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)])
def apply_asis(data: AsisApplyRequest, service: AsisSyncService = Depends(get_asis_sync_service)):
    if not data.company_ids and not data.branch_ids and data.category_ids == []:
        raise BadRequestError("Tidak ada data yang dipilih")
    service.apply_selected(data.company_ids, data.branch_ids, data.category_ids)
