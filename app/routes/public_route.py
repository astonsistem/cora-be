from typing import Annotated

from fastapi import Depends, Query

from app.core.response.envelope import ApiRouter
from app.dependencies import get_visit_stats_service
from app.middleware.api_key_middleware import api_key_required
from app.schemas.visit_stats_schema import VisitCountResponse
from app.services.visit_stats_service import VisitCountFilter, VisitStatsService

router = ApiRouter(prefix="/public", tags=["Public"], dependencies=[Depends(api_key_required)])

@router.get("/customer-visits/count", response_model=VisitCountResponse)
def count_customer_visits(
    criteria: Annotated[VisitCountFilter, Query()],
    service: VisitStatsService = Depends(get_visit_stats_service),
):
    return VisitCountResponse(count=service.count(criteria))
