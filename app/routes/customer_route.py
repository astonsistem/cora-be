import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status

from app.dependencies import (
    get_branch_service,
    get_customer_post_service,
    get_customer_service,
    get_customer_sync_service,
)
from app.exceptions import ConflictError, ForbiddenError
from app.middleware.auth_middleware import admin_only, get_current_user, manager_only
from app.models.users import Users
from app.schemas.customer_schema import (
    CustomerCreate,
    CustomerPostResponse,
    CustomerResponse,
    CustomerSyncRequest,
    CustomerUpdate,
)
from app.services.branch_service import BranchService
from app.services.customer_post_service import CustomerPostService
from app.services.customer_service import CustomerService
from app.services.customer_sync_service import CustomerSyncService

router = APIRouter(prefix="/customers", tags=["Customer"])

@router.post("/sync", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(admin_only)])
def sync_customers(
    background_tasks: BackgroundTasks,
    data: CustomerSyncRequest | None = None,
    branches: BranchService = Depends(get_branch_service),
    sync: CustomerSyncService = Depends(get_customer_sync_service),
    current_user: Users = Depends(get_current_user),
):
    branch_id = data.branch_id if data else None
    if branch_id:
        branch = branches.get_or_404(branch_id)
        if current_user.company_id is not None and branch.company_id != current_user.company_id:
            raise ForbiddenError("Branch tersebut bukan milik company Anda")
    if not sync.start(branch_id):
        raise ConflictError("Sync customer sedang berjalan")
    background_tasks.add_task(sync.run, branch_id, current_user.company_id)
    return sync.status()


@router.get("/sync/status", dependencies=[Depends(admin_only)])
def sync_customers_status(sync: CustomerSyncService = Depends(get_customer_sync_service)):
    return sync.status()


@router.get("/", response_model=list[CustomerResponse])
def list_customers(
    q: str | None = None,
    customer_status: str | None = Query(default=None, alias="status", pattern="^(posted|pending)$"),
    branch_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 50,
    response: Response = None,
    service: CustomerService = Depends(get_customer_service),
):
    response.headers["X-Total-Count"] = str(
        service.count_all(q=q, status=customer_status, branch_id=branch_id)
    )
    return service.get_all(skip=skip, limit=limit, q=q, status=customer_status, branch_id=branch_id)

@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: uuid.UUID, service: CustomerService = Depends(get_customer_service)):
    return service.get_or_404(customer_id)

@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(data: CustomerCreate, service: CustomerService = Depends(get_customer_service)):
    return service.create(data)

@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: uuid.UUID,
    data: CustomerUpdate,
    service: CustomerService = Depends(get_customer_service),
):
    return service.update(service.get_or_404(customer_id), data)

@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: uuid.UUID, service: CustomerService = Depends(get_customer_service)):
    service.delete(service.get_or_404(customer_id))

@router.post("/{customer_id}/post-to-asis", response_model=CustomerPostResponse, dependencies=[Depends(manager_only)])
def post_customer_to_asis(
    customer_id: uuid.UUID,
    service: CustomerService = Depends(get_customer_service),
    post_service: CustomerPostService = Depends(get_customer_post_service),
):
    customer, linked_existing = post_service.post(service.get_or_404(customer_id))
    return CustomerPostResponse.model_validate(customer).model_copy(update={"linked_existing": linked_existing})
