import uuid

from fastapi import BackgroundTasks, Depends, status

from app.core.response.envelope import ApiRouter
from app.dependencies import get_asis_sync_service, get_customer_sync_service
from app.exceptions import BadRequestError, ForbiddenError
from app.middleware.auth_middleware import admin_only, get_current_user, superadmin_only
from app.models.users import Users
from app.schemas.asis_schema import AsisApplyRequest
from app.services.asis_sync_service import AsisSyncService
from app.services.customer_sync_service import CustomerSyncService

router = ApiRouter(prefix="/asis", tags=["ASIS"])

@router.post("/sync", dependencies=[Depends(admin_only)])
def sync_asis(company_id: uuid.UUID | None = None, service: AsisSyncService = Depends(get_asis_sync_service)):
    return service.sync_all(company_id)

@router.get("/preview", dependencies=[Depends(admin_only)])
def preview_asis(company_id: uuid.UUID | None = None, service: AsisSyncService = Depends(get_asis_sync_service)):
    return service.preview(company_id)

@router.post("/apply", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)])
def apply_asis(
    data: AsisApplyRequest,
    service: AsisSyncService = Depends(get_asis_sync_service),
    current_user: Users = Depends(get_current_user),
):
    if data.company_ids and not current_user.is_superadmin:
        raise ForbiddenError("Only a superadmin can apply company changes")
    if not data.company_ids and not data.branch_ids and data.category_ids == []:
        raise BadRequestError("Tidak ada data yang dipilih")
    service.apply_selected(data.company_ids, data.branch_ids, data.category_ids, data.company_id)

@router.post("/companies/{company_id}/initial-sync", dependencies=[Depends(superadmin_only)])
def initial_sync(
    company_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    service: AsisSyncService = Depends(get_asis_sync_service),
    customers: CustomerSyncService = Depends(get_customer_sync_service),
):
    result = service.initial_sync(company_id)
    customers_started = customers.start(None)
    if customers_started:
        background_tasks.add_task(customers.run, None, company_id)
    return {**result, "customers_started": customers_started, "customers": customers.status()}
