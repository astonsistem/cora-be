import uuid

from fastapi import Depends, status

from app.core.response.envelope import ApiRouter
from app.dependencies import get_qr_visit_service, get_voucher_issue_service, get_voucher_redeem_service
from app.middleware.rate_limit_middleware import code_guard, public_guard, submit_guard
from app.schemas.voucher_qr_schema import (
    IssuedVouchers,
    QrClaimRequest,
    QrLinkTarget,
    QrPublicInfo,
    QrSubmit,
    QrSubmitResult,
)
from app.schemas.voucher_schema import CodeView, PublicClaimCreate
from app.services.qr_visit_service import QrVisitService
from app.services.voucher_issue_service import VoucherIssueService
from app.services.voucher_redeem_service import VoucherRedeemService

router = ApiRouter(prefix="/public", tags=["Public Voucher"])

@router.get("/qr/{code}", response_model=QrPublicInfo, dependencies=[Depends(public_guard)])
def qr_info(code: str, service: QrVisitService = Depends(get_qr_visit_service)):
    return service.info(code)

@router.post(
    "/qr/{code}/submit",
    response_model=QrSubmitResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(submit_guard)],
)
def qr_submit(code: str, data: QrSubmit, service: QrVisitService = Depends(get_qr_visit_service)):
    return service.submit(code, data)

@router.get("/voucher-links/{slug}", response_model=QrLinkTarget, dependencies=[Depends(public_guard)])
def voucher_link(slug: str, service: QrVisitService = Depends(get_qr_visit_service)):
    return service.resolve_link(slug)

@router.post(
    "/qr-claims/{token}/claim",
    response_model=IssuedVouchers,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(code_guard)],
)
def claim_vouchers(
    token: str,
    data: QrClaimRequest = QrClaimRequest(),
    service: VoucherIssueService = Depends(get_voucher_issue_service),
):
    codes = service.claim(token, data.voucher_id)
    return {
        "vouchers": [
            {
                "voucher_id": item.voucher.voucher_id,
                "voucher_name": item.voucher.voucher_name,
                "description": item.voucher.description,
                "date_expired": item.voucher.date_expired,
                "design": item.voucher.design,
                "code": item.code,
            }
            for item in codes
        ]
    }

@router.get("/voucher-codes/{code}", response_model=CodeView, dependencies=[Depends(code_guard)])
def lookup_code(code: str, service: VoucherRedeemService = Depends(get_voucher_redeem_service)):
    return service.view(code)

@router.post(
    "/voucher-codes/{code}/claim",
    response_model=CodeView,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(code_guard)],
)
def claim_code(
    code: str,
    data: PublicClaimCreate,
    service: VoucherRedeemService = Depends(get_voucher_redeem_service),
):
    return service.claim(code, data.branch_id)

@router.post(
    "/voucher-codes/{code}/claims/{claim_id}/cancel",
    response_model=CodeView,
    dependencies=[Depends(code_guard)],
)
def cancel_claim(
    code: str,
    claim_id: uuid.UUID,
    service: VoucherRedeemService = Depends(get_voucher_redeem_service),
):
    return service.cancel(code, claim_id)
