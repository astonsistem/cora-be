import uuid

from fastapi import Depends, Query, Response, status

from app.core.response.envelope import ApiRouter
from app.dependencies import get_voucher_claim_service
from app.middleware.auth_middleware import admin_only
from app.models.voucher import ClaimStatus
from app.schemas.voucher_schema import ClaimCreate, ClaimRecord
from app.services.voucher_claim_service import VoucherClaimService

router = ApiRouter(prefix="/voucher-claims", tags=["Voucher Claim"])

@router.get("/", response_model=list[ClaimRecord])
def list_claims(
    claim_status: ClaimStatus | None = Query(default=None, alias="status"),
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
    response: Response = None,
    service: VoucherClaimService = Depends(get_voucher_claim_service),
):
    response.headers["X-Total-Count"] = str(service.count_all(claim_status, search))
    claims = service.get_all(skip=skip, limit=limit, status=claim_status, search=search)
    return [service.to_record(claim) for claim in claims]

@router.post("/", response_model=ClaimRecord, status_code=status.HTTP_201_CREATED)
def create_claim(data: ClaimCreate, service: VoucherClaimService = Depends(get_voucher_claim_service)):
    return service.to_record(service.create(data))

@router.patch("/{claim_id}/approve", response_model=ClaimRecord)
def approve_claim(claim_id: uuid.UUID, service: VoucherClaimService = Depends(get_voucher_claim_service)):
    return service.to_record(service.approve(claim_id))

@router.patch("/{claim_id}/clear-flag", response_model=ClaimRecord, dependencies=[Depends(admin_only)])
def clear_claim_flag(claim_id: uuid.UUID, service: VoucherClaimService = Depends(get_voucher_claim_service)):
    return service.to_record(service.clear_flag(claim_id))
