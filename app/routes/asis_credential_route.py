import uuid

from fastapi import Depends, status

from app.core.response.envelope import ApiRouter
from app.dependencies import get_activity_logger, get_asis_credential_service
from app.middleware.auth_middleware import admin_only
from app.models.users import Users
from app.schemas.asis_credential_schema import AsisBranchCredentialResponse, AsisCredentialResponse, AsisCredentialSet
from app.models.branches import Branches
from app.models.companies import Companies
from app.services.activity_logger import Action, ActivityLogger, Module
from app.services.asis_credential_service import AsisCredentialService

router = ApiRouter(prefix="/asis/credentials", tags=["ASIS"])

@router.get("/", response_model=list[AsisCredentialResponse])
def list_credentials(
    service: AsisCredentialService = Depends(get_asis_credential_service),
    current_user: Users = Depends(admin_only),
):
    return service.list_all(current_user)

@router.get("/branches", response_model=list[AsisBranchCredentialResponse])
def list_branch_credentials(
    service: AsisCredentialService = Depends(get_asis_credential_service),
    current_user: Users = Depends(admin_only),
):
    return service.list_branches(current_user)

@router.put("/branches/{branch_id}", response_model=AsisBranchCredentialResponse)
def save_branch_credential(
    branch_id: uuid.UUID,
    data: AsisCredentialSet,
    service: AsisCredentialService = Depends(get_asis_credential_service),
    current_user: Users = Depends(admin_only),
    activity: ActivityLogger = Depends(get_activity_logger),
):
    credential = service.save_branch(branch_id, data, current_user)
    activity.record(Action.update, Module.asis, f'Mengatur akun ASIS branch "{credential["branch_name"]}"')
    return credential

@router.delete("/branches/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_branch_credential(
    branch_id: uuid.UUID,
    service: AsisCredentialService = Depends(get_asis_credential_service),
    current_user: Users = Depends(admin_only),
    activity: ActivityLogger = Depends(get_activity_logger),
):
    branch = activity.db.get(Branches, branch_id)
    name = branch.branch_name if branch else "-"
    service.remove_branch(branch_id, current_user)
    activity.record(Action.delete, Module.asis, f'Menghapus akun ASIS branch "{name}"')

@router.put("/{company_id}", response_model=AsisCredentialResponse)
def save_credential(
    company_id: uuid.UUID,
    data: AsisCredentialSet,
    service: AsisCredentialService = Depends(get_asis_credential_service),
    current_user: Users = Depends(admin_only),
    activity: ActivityLogger = Depends(get_activity_logger),
):
    credential = service.save(company_id, data, current_user)
    activity.record(Action.update, Module.asis, f'Mengatur akun ASIS company "{credential["company_name"]}"')
    return credential

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(
    company_id: uuid.UUID,
    service: AsisCredentialService = Depends(get_asis_credential_service),
    current_user: Users = Depends(admin_only),
    activity: ActivityLogger = Depends(get_activity_logger),
):
    company = activity.db.get(Companies, company_id)
    name = company.company_name if company else "-"
    service.remove(company_id, current_user)
    activity.record(Action.delete, Module.asis, f'Menghapus akun ASIS company "{name}"')
