import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth_middleware import admin_only, get_current_user
from app.models.users import UserRole, Users
from app.schemas.customer_visit_schema import (
    CustomerVisitCreate,
    CustomerVisitResponse,
    CustomerVisitSummary,
    CustomerVisitUpdate,
)
from app.services import asis_post_service, customer_visit_service

router = APIRouter(prefix="/customer-visits", tags=["Customer Visit"])


def _get_or_404(db: Session, visit_id: uuid.UUID, current_user: Users):
    visit = customer_visit_service.get_by_id(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Customer visit not found")
    if current_user.user_role == UserRole.sales and visit.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You can only access your own visits")
    return visit


@router.get("/", response_model=list[CustomerVisitResponse])
def list_visits(
    user_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    skip: int = 0,
    limit: int = 100,
    response: Response = None,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    # Jumlah seluruh data (tanpa skip dan limit) untuk pagination.
    response.headers["X-Total-Count"] = str(
        customer_visit_service.count_all(db, current_user, user_id=user_id, date_from=date_from, date_to=date_to)
    )
    return customer_visit_service.get_all(
        db, current_user, user_id=user_id, date_from=date_from, date_to=date_to, skip=skip, limit=limit
    )


@router.get("/summary", response_model=CustomerVisitSummary)
def visit_summary(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    return customer_visit_service.get_summary(db, current_user, date_from=date_from, date_to=date_to)


@router.get("/{visit_id}", response_model=CustomerVisitResponse)
def get_visit(
    visit_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    return _get_or_404(db, visit_id, current_user)


@router.post("/", response_model=CustomerVisitResponse, status_code=status.HTTP_201_CREATED)
def create_visit(
    data: CustomerVisitCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    try:
        return customer_visit_service.create_visit(db, data, current_user)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid source or category reference")


@router.post("/{visit_id}/post-to-asis", response_model=CustomerVisitResponse, dependencies=[Depends(admin_only)])
def post_visit_to_asis(
    visit_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    visit = _get_or_404(db, visit_id, current_user)
    try:
        return asis_post_service.post_visit(db, visit)
    except asis_post_service.AlreadyPostedError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except asis_post_service.VisitPostError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{visit_id}", response_model=CustomerVisitResponse)
def update_visit(
    visit_id: uuid.UUID,
    data: CustomerVisitUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    visit = _get_or_404(db, visit_id, current_user)
    try:
        return customer_visit_service.update_visit(db, visit, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid source or category reference")


@router.delete("/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visit(
    visit_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    visit = _get_or_404(db, visit_id, current_user)
    customer_visit_service.delete_visit(db, visit)
