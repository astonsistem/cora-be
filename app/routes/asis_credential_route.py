import uuid

from fastapi import Depends, status

from app.core.response.envelope import ApiRouter
from app.dependencies import get_asis_credential_service
from app.middleware.auth_middleware import admin_only
from app.models.users import Users
from app.schemas.asis_credential_schema import AsisCredentialResponse, AsisCredentialSet
from app.services.asis_credential_service import AsisCredentialService

router = ApiRouter(prefix="/asis/credentials", tags=["ASIS"])

@router.get("/", response_model=list[AsisCredentialResponse])
def list_credentials(
    service: AsisCredentialService = Depends(get_asis_credential_service),
    current_user: Users = Depends(admin_only),
):
    return service.list_all(current_user)

@router.put("/{company_id}", response_model=AsisCredentialResponse)
def save_credential(
    company_id: uuid.UUID,
    data: AsisCredentialSet,
    service: AsisCredentialService = Depends(get_asis_credential_service),
    current_user: Users = Depends(admin_only),
):
    return service.save(company_id, data, current_user)

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(
    company_id: uuid.UUID,
    service: AsisCredentialService = Depends(get_asis_credential_service),
    current_user: Users = Depends(admin_only),
):
    service.remove(company_id, current_user)
