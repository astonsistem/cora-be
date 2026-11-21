import uuid

from fastapi import Depends, Response, status

from app.core.response.envelope import ApiRouter
from app.dependencies import get_voucher_qr_service
from app.middleware.auth_middleware import admin_only, om_only
from app.schemas.voucher_qr_schema import VoucherQrCreate, VoucherQrResponse, VoucherQrUpdate
from app.services.voucher_qr_service import VoucherQrService

router = ApiRouter(prefix="/voucher-qrs", tags=["Voucher QR"])

@router.get("/", response_model=list[VoucherQrResponse], dependencies=[Depends(admin_only)])
def list_qrs(skip: int = 0, limit: int = 100, service: VoucherQrService = Depends(get_voucher_qr_service)):
    return service.get_all(skip=skip, limit=limit)

@router.post(
    "/",
    response_model=VoucherQrResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(om_only)],
)
def create_qr(data: VoucherQrCreate, service: VoucherQrService = Depends(get_voucher_qr_service)):
    return service.create(data)

@router.get("/{qr_id}", response_model=VoucherQrResponse, dependencies=[Depends(admin_only)])
def get_qr(qr_id: uuid.UUID, service: VoucherQrService = Depends(get_voucher_qr_service)):
    return service.get_or_404(qr_id)

@router.patch("/{qr_id}", response_model=VoucherQrResponse, dependencies=[Depends(om_only)])
def update_qr(qr_id: uuid.UUID, data: VoucherQrUpdate, service: VoucherQrService = Depends(get_voucher_qr_service)):
    return service.update(service.get_or_404(qr_id), data)

@router.post("/{qr_id}/regenerate-code", response_model=VoucherQrResponse, dependencies=[Depends(om_only)])
def regenerate_qr_code(qr_id: uuid.UUID, service: VoucherQrService = Depends(get_voucher_qr_service)):
    return service.regenerate_code(service.get_or_404(qr_id))

@router.delete("/{qr_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(om_only)])
def delete_qr(qr_id: uuid.UUID, service: VoucherQrService = Depends(get_voucher_qr_service)):
    service.delete(service.get_or_404(qr_id))
