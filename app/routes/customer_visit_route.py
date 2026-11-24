import uuid
from datetime import date

from fastapi import Depends, Response, status

from app.core.response.envelope import ApiRouter
from app.dependencies import get_activity_logger, get_customer_visit_service
from app.middleware.auth_middleware import manager_only
from app.schemas.customer_visit_schema import (
    CustomerVisitCreate,
    CustomerVisitResponse,
    CustomerVisitSummary,
    CustomerVisitUpdate,
)
from app.services import asis_post_service
from app.services.activity_logger import Action, ActivityLogger, Module
from app.services.customer_visit_service import CustomerVisitService

router = ApiRouter(prefix="/customer-visits", tags=["Customer Visit"])

@router.get("/", response_model=list[CustomerVisitResponse])
def list_visits(
    user_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    skip: int = 0,
    limit: int = 100,
    response: Response = None,
    service: CustomerVisitService = Depends(get_customer_visit_service),
):
    response.headers["X-Total-Count"] = str(
        service.count_all(user_id=user_id, date_from=date_from, date_to=date_to)
    )
    return service.get_all(skip=skip, limit=limit, user_id=user_id, date_from=date_from, date_to=date_to)

@router.get("/summary", response_model=CustomerVisitSummary)
def visit_summary(
    date_from: date | None = None,
    date_to: date | None = None,
    service: CustomerVisitService = Depends(get_customer_visit_service),
):
    return service.get_summary(date_from=date_from, date_to=date_to)

@router.get("/{visit_id}", response_model=CustomerVisitResponse)
def get_visit(visit_id: uuid.UUID, service: CustomerVisitService = Depends(get_customer_visit_service)):
    return service.get_or_404(visit_id)

@router.post("/", response_model=CustomerVisitResponse, status_code=status.HTTP_201_CREATED)
def create_visit(
    data: CustomerVisitCreate,
    service: CustomerVisitService = Depends(get_customer_visit_service),
    activity: ActivityLogger = Depends(get_activity_logger),
):
    visit = service.create(data)
    activity.created(Module.customer_visit, "customer visit", visit.customer_name)
    return visit

@router.post("/{visit_id}/post-to-asis", response_model=CustomerVisitResponse, dependencies=[Depends(manager_only)])
def post_visit_to_asis(
    visit_id: uuid.UUID,
    service: CustomerVisitService = Depends(get_customer_visit_service),
    activity: ActivityLogger = Depends(get_activity_logger),
):
    visit = service.get_or_404(visit_id)
    posted = asis_post_service.post_visit(service.db, visit, service.user)
    activity.record(Action.post, Module.asis, f'Posting customer "{posted.customer_name}" ke ASIS')
    return posted

@router.patch("/{visit_id}", response_model=CustomerVisitResponse)
def update_visit(
    visit_id: uuid.UUID,
    data: CustomerVisitUpdate,
    service: CustomerVisitService = Depends(get_customer_visit_service),
    activity: ActivityLogger = Depends(get_activity_logger),
):
    visit = service.update(service.get_or_404(visit_id), data)
    activity.updated(Module.customer_visit, "customer visit", visit.customer_name)
    return visit

@router.delete("/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visit(
    visit_id: uuid.UUID,
    service: CustomerVisitService = Depends(get_customer_visit_service),
    activity: ActivityLogger = Depends(get_activity_logger),
):
    visit = service.get_or_404(visit_id)
    name = visit.customer_name
    service.delete(visit)
    activity.deleted(Module.customer_visit, "customer visit", name)
