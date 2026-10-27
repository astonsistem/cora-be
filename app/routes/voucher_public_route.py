from fastapi import APIRouter, Depends, status

from app.dependencies import get_voucher_redemption_service
from app.middleware.api_key_middleware import api_key_required
from app.schemas.voucher_schema import (
    PublicRedemptionCreate,
    PublicRedemptionResult,
    PublicVoucherItem,
)
from app.services.voucher_redemption_service import VoucherRedemptionService

router = APIRouter(
    prefix="/public/vouchers",
    tags=["Public Voucher"],
)


@router.get("/active", response_model=list[PublicVoucherItem])
def active_vouchers(service: VoucherRedemptionService = Depends(get_voucher_redemption_service)):
    return service.list_active()


@router.post("/redeem", response_model=PublicRedemptionResult, status_code=status.HTTP_201_CREATED)
def redeem_voucher(
    data: PublicRedemptionCreate,
    service: VoucherRedemptionService = Depends(get_voucher_redemption_service),
):
    service.redeem(data)
    return PublicRedemptionResult(message="Penukaran voucher berhasil dicatat")