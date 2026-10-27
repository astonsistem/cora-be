import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status

from app.dependencies import get_voucher_service
from app.middleware.auth_middleware import manager_only
from app.schemas.voucher_schema import (
    RedemptionResponse,
    RedemptionStatus,
    RedemptionStatusUpdate,
    VoucherCreate,
    VoucherResponse,
    VoucherUpdate,
)
from app.services.voucher_service import VoucherService

router = APIRouter(
    prefix="/vouchers",
    tags=["Voucher"],
    dependencies=[Depends(manager_only)],
)


@router.get("/", response_model=list[VoucherResponse])
def list_vouchers(
    is_active: bool | None = None,
    branch_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    response: Response = None,
    service: VoucherService = Depends(get_voucher_service),
):
    response.headers["X-Total-Count"] = str(service.count_all(is_active, branch_id))
    return service.get_all(skip=skip, limit=limit, is_active=is_active, branch_id=branch_id)


@router.post("/", response_model=VoucherResponse, status_code=status.HTTP_201_CREATED)
def create_voucher(data: VoucherCreate, service: VoucherService = Depends(get_voucher_service)):
    return service.create(data)


# Penting: route "/redemptions" harus di atas "/{voucher_id}"
@router.get("/redemptions", response_model=list[RedemptionResponse])
def list_redemptions(
    voucher_id: uuid.UUID | None = None,
    redemption_status: RedemptionStatus | None = Query(default=None, alias="status"),
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    skip: int = 0,
    limit: int = 100,
    response: Response = None,
    service: VoucherService = Depends(get_voucher_service),
):
    response.headers["X-Total-Count"] = str(
        service.count_redemptions(voucher_id, redemption_status, search, date_from, date_to)
    )
    return service.get_redemptions(
        skip=skip, limit=limit, voucher_id=voucher_id, status=redemption_status,
        search=search, date_from=date_from, date_to=date_to,
    )


@router.patch("/redemptions/{redemption_id}", response_model=RedemptionResponse)
def update_redemption_status(
    redemption_id: uuid.UUID,
    data: RedemptionStatusUpdate,
    service: VoucherService = Depends(get_voucher_service),
):
    return service.update_redemption_status(redemption_id, data.status)


@router.get("/{voucher_id}", response_model=VoucherResponse)
def get_voucher(voucher_id: uuid.UUID, service: VoucherService = Depends(get_voucher_service)):
    return service.get_or_404(voucher_id)


@router.patch("/{voucher_id}", response_model=VoucherResponse)
def update_voucher(
    voucher_id: uuid.UUID,
    data: VoucherUpdate,
    service: VoucherService = Depends(get_voucher_service),
):
    return service.update(service.get_or_404(voucher_id), data)


@router.delete("/{voucher_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_voucher(voucher_id: uuid.UUID, service: VoucherService = Depends(get_voucher_service)):
    service.delete(service.get_or_404(voucher_id))