import uuid

from fastapi import Depends, Response, status

from app.core.response.envelope import ApiRouter
from app.dependencies import get_voucher_service
from app.middleware.auth_middleware import admin_only, manager_only
from app.models.voucher import VoucherStatus
from app.schemas.voucher_schema import VoucherCreate, VoucherDesignUpdate, VoucherResponse, VoucherUpdate
from app.services.voucher_service import VoucherService

router = ApiRouter(prefix="/vouchers", tags=["Voucher"])

@router.get("/", response_model=list[VoucherResponse], dependencies=[Depends(manager_only)])
def list_vouchers(
    voucher_status: VoucherStatus | None = None,
    company_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    response: Response = None,
    service: VoucherService = Depends(get_voucher_service),
):
    status_value = voucher_status.value if voucher_status else None
    response.headers["X-Total-Count"] = str(service.count_all(status_value, company_id))
    return service.get_all(skip=skip, limit=limit, status=status_value, company_id=company_id)

@router.get("/archived", response_model=list[VoucherResponse], dependencies=[Depends(manager_only)])
def list_archived_vouchers(
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
    response: Response = None,
    service: VoucherService = Depends(get_voucher_service),
):
    response.headers["X-Total-Count"] = str(service.count_archived(search))
    return service.get_archived(skip=skip, limit=limit, search=search)

@router.post(
    "/",
    response_model=VoucherResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_only)],
)
def create_voucher(data: VoucherCreate, service: VoucherService = Depends(get_voucher_service)):
    return service.create(data)

@router.get("/{voucher_id}", response_model=VoucherResponse, dependencies=[Depends(manager_only)])
def get_voucher(voucher_id: uuid.UUID, service: VoucherService = Depends(get_voucher_service)):
    return service.get_or_404(voucher_id)

@router.patch("/{voucher_id}", response_model=VoucherResponse, dependencies=[Depends(admin_only)])
def update_voucher(
    voucher_id: uuid.UUID,
    data: VoucherUpdate,
    service: VoucherService = Depends(get_voucher_service),
):
    return service.update(service.get_or_404(voucher_id), data)

@router.patch("/{voucher_id}/design", response_model=VoucherResponse, dependencies=[Depends(admin_only)])
def update_voucher_design(
    voucher_id: uuid.UUID,
    data: VoucherDesignUpdate,
    service: VoucherService = Depends(get_voucher_service),
):
    return service.update_design(service.get_or_404(voucher_id), data.design)

@router.delete("/{voucher_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)])
def delete_voucher(voucher_id: uuid.UUID, service: VoucherService = Depends(get_voucher_service)):
    service.delete(service.get_or_404(voucher_id))
