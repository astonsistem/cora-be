import uuid

from fastapi import Depends, Response, status

from app.core.response.envelope import ApiRouter
from app.dependencies import get_activity_logger, get_voucher_qr_service
from app.middleware.auth_middleware import admin_only
from app.schemas.voucher_qr_schema import VoucherQrCreate, VoucherQrResponse, VoucherQrUpdate
from app.services.activity_logger import Action, ActivityLogger, Module
from app.services.voucher_qr_service import VoucherQrService

router = ApiRouter(prefix="/voucher-qrs", tags=["Voucher QR"])

@router.get("/", response_model=list[VoucherQrResponse], dependencies=[Depends(admin_only)])
def list_qrs(skip: int = 0, limit: int = 100, service: VoucherQrService = Depends(get_voucher_qr_service)):
    return service.get_all(skip=skip, limit=limit)

@router.post(
    "/",
    response_model=VoucherQrResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_only)],
)
def create_qr(
    data: VoucherQrCreate,
    service: VoucherQrService = Depends(get_voucher_qr_service),
    activity: ActivityLogger = Depends(get_activity_logger),
):
    qr = service.create(data)
    activity.created(Module.qr, "QR", qr.name)
    return qr

@router.get("/{qr_id}", response_model=VoucherQrResponse, dependencies=[Depends(admin_only)])
def get_qr(qr_id: uuid.UUID, service: VoucherQrService = Depends(get_voucher_qr_service)):
    return service.get_or_404(qr_id)

@router.patch("/{qr_id}", response_model=VoucherQrResponse, dependencies=[Depends(admin_only)])
def update_qr(
    qr_id: uuid.UUID,
    data: VoucherQrUpdate,
    service: VoucherQrService = Depends(get_voucher_qr_service),
    activity: ActivityLogger = Depends(get_activity_logger),
):
    changes = data.model_dump(exclude_unset=True)
    qr = service.update(service.get_or_404(qr_id), data)
    if set(changes) == {"is_locked"} and changes["is_locked"] is not None:
        verb = "Mengunci" if qr.is_locked else "Membuka kunci"
        activity.record(Action.update, Module.qr, f'{verb} kode QR "{qr.name}"')
    else:
        activity.record(Action.update, Module.qr, f'Mengubah pengaturan QR "{qr.name}"')
    return qr

@router.post("/{qr_id}/regenerate-code", response_model=VoucherQrResponse, dependencies=[Depends(admin_only)])
def regenerate_qr_code(
    qr_id: uuid.UUID,
    service: VoucherQrService = Depends(get_voucher_qr_service),
    activity: ActivityLogger = Depends(get_activity_logger),
):
    qr = service.regenerate_code(service.get_or_404(qr_id))
    activity.record(Action.update, Module.qr, f'Generate ulang kode QR "{qr.name}"')
    return qr

@router.delete("/{qr_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(admin_only)])
def delete_qr(
    qr_id: uuid.UUID,
    service: VoucherQrService = Depends(get_voucher_qr_service),
    activity: ActivityLogger = Depends(get_activity_logger),
):
    qr = service.get_or_404(qr_id)
    name = qr.name
    service.delete(qr)
    activity.deleted(Module.qr, "QR", name)
