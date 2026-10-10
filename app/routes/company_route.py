import uuid

from fastapi import APIRouter, Depends, status

from app.dependencies import get_company_service
from app.middleware.auth_middleware import admin_only, get_current_user
from app.schemas.company_schema import CompanyCreate, CompanyResponse, CompanyUpdate
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["Company"], dependencies=[Depends(admin_only)])

@router.get("/", response_model=list[CompanyResponse])
def list_items(skip: int = 0, limit: int = 100, service: CompanyService = Depends(get_company_service)):
    return service.get_all(skip=skip, limit=limit)

@router.get("/{company_id}", response_model=CompanyResponse)
def get_item(company_id: uuid.UUID, service: CompanyService = Depends(get_company_service)):
    return service.get_or_404(company_id)

@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_item(data: CompanyCreate, service: CompanyService = Depends(get_company_service)):
    return service.create(data)

@router.patch("/{company_id}", response_model=CompanyResponse)
def update_item(company_id: uuid.UUID, data: CompanyUpdate, service: CompanyService = Depends(get_company_service)):
    return service.update(service.get_or_404(company_id), data)

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(company_id: uuid.UUID, service: CompanyService = Depends(get_company_service)):
    service.delete(service.get_or_404(company_id))
