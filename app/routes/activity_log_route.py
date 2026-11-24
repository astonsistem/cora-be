import uuid
from datetime import date

from fastapi import Depends, Query, Response

from app.core.response.envelope import ApiRouter
from app.dependencies import get_activity_log_service
from app.middleware.auth_middleware import admin_only, superadmin_only
from app.schemas.activity_log_schema import ActivityFilterOptions, ActivityLogResponse
from app.services.activity_log_service import ActivityLogService

router = ApiRouter(prefix="/activity-logs", tags=["Activity Log"], dependencies=[Depends(admin_only)])

def _list(
    response: Response,
    service: ActivityLogService,
    archived: bool,
    skip: int,
    limit: int,
    sort_by: str | None,
    sort_order: str | None,
    filters: dict,
):
    response.headers["X-Total-Count"] = str(service.count_all(archived=archived, **filters))
    return service.get_all(
        skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order, archived=archived, **filters
    )

def _filters(q, action, module, company_id, branch_id, date_from, date_to) -> dict:
    return {
        "q": q,
        "action": action,
        "module": module,
        "company_id": company_id,
        "branch_id": branch_id,
        "date_from": date_from,
        "date_to": date_to,
    }

@router.get("/filter-options", response_model=ActivityFilterOptions)
def filter_options(service: ActivityLogService = Depends(get_activity_log_service)):
    return service.filter_options()

@router.get("/archived", response_model=list[ActivityLogResponse], dependencies=[Depends(superadmin_only)])
def list_archived_logs(
    q: str | None = None,
    action: str | None = None,
    module: str | None = None,
    company_id: uuid.UUID | None = None,
    branch_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: str | None = None,
    sort_order: str | None = Query(default=None, pattern="^(asc|desc)$"),
    skip: int = 0,
    limit: int = 10,
    response: Response = None,
    service: ActivityLogService = Depends(get_activity_log_service),
):
    filters = _filters(q, action, module, company_id, branch_id, date_from, date_to)
    return _list(response, service, True, skip, limit, sort_by, sort_order, filters)

@router.get("/", response_model=list[ActivityLogResponse])
def list_logs(
    q: str | None = None,
    action: str | None = None,
    module: str | None = None,
    company_id: uuid.UUID | None = None,
    branch_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: str | None = None,
    sort_order: str | None = Query(default=None, pattern="^(asc|desc)$"),
    skip: int = 0,
    limit: int = 10,
    response: Response = None,
    service: ActivityLogService = Depends(get_activity_log_service),
):
    filters = _filters(q, action, module, company_id, branch_id, date_from, date_to)
    return _list(response, service, False, skip, limit, sort_by, sort_order, filters)
