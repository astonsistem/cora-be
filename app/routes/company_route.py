import uuid

from fastapi import Depends, Response, status

from app.core.response.envelope import ApiRouter
from app.dependencies import get_activity_logger, get_company_service
from app.middleware.auth_middleware import admin_only, superadmin_only
from app.models.users import Users
from app.schemas.company_schema import CompanyCreate, CompanyResponse, CompanyUpdate
from app.services.activity_logger import Action, ActivityLogger, Module
from app.services.company_service import CompanyService

router = ApiRouter(prefix="/companies", tags=["Company"])

@router.get("/", response_model=list[CompanyResponse])
def list_items(
    skip: int = 0,
    limit: int = 100,
    service: CompanyService = Depends(get_company_service),
    current_user: Users = Depends(admin_only),
):
    return service.get_all_for(current_user, skip=skip, limit=limit)

@router.get("/deleted", response_model=list[CompanyResponse], dependencies=[Depends(superadmin_only)])
def list_deleted_items(
    q: str | None = None,
    skip: int = 0,
    limit: int = 50,
    response: Response = None,
    service: CompanyService = Depends(get_company_service),
):
    response.headers["X-Total-Count"] = str(service.count_deleted(q=q))
    return service.get_deleted(skip=skip, limit=limit, q=q)

@router.get("/{company_id}", response_model=CompanyResponse)
def get_item(
    company_id: uuid.UUID,
    service: CompanyService = Depends(get_company_service),
    current_user: Users = Depends(admin_only),
):
    return service.get_for_or_404(current_user, company_id)

@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(superadmin_only)])
def create_item(
    data: CompanyCreate,
    service: CompanyService = Depends(get_company_service),
    activity: ActivityLogger = Depends(get_activity_logger),
):
    company = service.create(data)
    activity.created(Module.master, "company", company.company_name)
    return company

@router.patch("/{company_id}", response_model=CompanyResponse, dependencies=[Depends(superadmin_only)])
def update_item(
    company_id: uuid.UUID,
    data: CompanyUpdate,
    service: CompanyService = Depends(get_company_service),
    activity: ActivityLogger = Depends(get_activity_logger),
):
    company = service.update(service.get_or_404(company_id), data)
    activity.updated(Module.master, "company", company.company_name)
    return company

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(superadmin_only)])
def delete_item(
    company_id: uuid.UUID,
    service: CompanyService = Depends(get_company_service),
    activity: ActivityLogger = Depends(get_activity_logger),
):
    company = service.get_or_404(company_id)
    name = company.company_name
    service.delete(company)
    activity.deleted(Module.master, "company", name)

@router.post("/{company_id}/restore", response_model=CompanyResponse, dependencies=[Depends(superadmin_only)])
def restore_item(
    company_id: uuid.UUID,
    service: CompanyService = Depends(get_company_service),
    activity: ActivityLogger = Depends(get_activity_logger),
):
    company = service.restore(service.get_deleted_or_404(company_id))
    activity.restored(Module.master, "company", company.company_name)
    return company