import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth_middleware import admin_only, get_current_user, manager_only
from app.models.branches import Branches
from app.models.users import Users
from app.schemas.customer_schema import (
    CustomerCreate,
    CustomerPostResponse,
    CustomerResponse,
    CustomerSyncRequest,
    CustomerUpdate,
)
from app.services import customer_post_service, customer_service, customer_sync_service

router = APIRouter(prefix="/customers", tags=["Customer"])

def _get_or_404(db: Session, user: Users, customer_id: uuid.UUID):
    customer = customer_service.get_for_user(db, user, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.post("/sync", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(admin_only)])
def sync_customers(
    background_tasks: BackgroundTasks,
    data: CustomerSyncRequest | None = None,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    branch_id = data.branch_id if data else None
    if branch_id:
        branch = db.get(Branches, branch_id)
        if branch is None:
            raise HTTPException(status_code=404, detail="Branch not found")
        if current_user.company_id is not None and branch.company_id != current_user.company_id:
            raise HTTPException(status_code=403, detail="Branch tersebut bukan milik company Anda")
    if not customer_sync_service.start(branch_id):
        raise HTTPException(status_code=409, detail="Sync customer sedang berjalan")
    background_tasks.add_task(customer_sync_service.run, branch_id, current_user.company_id)
    return customer_sync_service.get_status()


@router.get("/sync/status", dependencies=[Depends(admin_only)])
def sync_customers_status():
    return customer_sync_service.get_status()


@router.get("/", response_model=list[CustomerResponse])
def list_customers(
    q: str | None = None,
    customer_status: str | None = Query(default=None, alias="status", pattern="^(posted|pending)$"),
    branch_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 50,
    response: Response = None,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    response.headers["X-Total-Count"] = str(
        customer_service.count_all(db, current_user, q=q, status=customer_status, branch_id=branch_id)
    )
    return customer_service.get_all(
        db, current_user, q=q, status=customer_status, branch_id=branch_id, skip=skip, limit=limit
    )

@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    return _get_or_404(db, current_user, customer_id)

@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    try:
        return customer_service.create_customer(db, current_user, data)
    except customer_service.DuplicateCustomerError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid category or branch reference")

@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: uuid.UUID,
    data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    customer = _get_or_404(db, current_user, customer_id)
    try:
        return customer_service.update_customer(db, current_user, customer, data)
    except (customer_service.DuplicateCustomerError, customer_service.CustomerPostedError) as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid category or branch reference")

@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    customer = _get_or_404(db, current_user, customer_id)
    try:
        customer_service.delete_customer(db, customer)
    except customer_service.CustomerPostedError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Customer masih dipakai oleh customer visit")

@router.post("/{customer_id}/post-to-asis", response_model=CustomerPostResponse, dependencies=[Depends(manager_only)])
def post_customer_to_asis(
    customer_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    customer = _get_or_404(db, current_user, customer_id)
    try:
        customer, linked_existing = customer_post_service.post_customer(db, customer)
    except customer_post_service.AlreadyPostedError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except customer_post_service.PostError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return CustomerPostResponse.model_validate(customer).model_copy(update={"linked_existing": linked_existing})
