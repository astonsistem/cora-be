from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.users import Users
from app.services.asis_sync_service import AsisSyncService
from app.services.branch_service import BranchService
from app.services.category_service import CategoryService
from app.services.company_service import CompanyService
from app.services.customer_post_service import CustomerPostService
from app.services.customer_service import CustomerService
from app.services.customer_sync_service import CustomerSyncService, SyncState
from app.services.customer_visit_service import CustomerVisitService
from app.services.report_service import ReportService
from app.services.source_service import SourceService
from app.services.user_service import UserService
from app.services.visit_stats_service import VisitStatsService

def get_branch_service(db: Session = Depends(get_db)) -> BranchService:
    return BranchService(db)

def get_category_service(db: Session = Depends(get_db)) -> CategoryService:
    return CategoryService(db)

def get_company_service(db: Session = Depends(get_db)) -> CompanyService:
    return CompanyService(db)

def get_source_service(db: Session = Depends(get_db)) -> SourceService:
    return SourceService(db)

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)

def get_customer_service(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
) -> CustomerService:
    return CustomerService(db, current_user)

def get_customer_visit_service(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
) -> CustomerVisitService:
    return CustomerVisitService(db, current_user)

def get_report_service(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
) -> ReportService:
    return ReportService(db, current_user)

def get_visit_stats_service(db: Session = Depends(get_db)) -> VisitStatsService:
    return VisitStatsService(db)

def get_customer_post_service(db: Session = Depends(get_db)) -> CustomerPostService:
    return CustomerPostService(db)

def get_asis_sync_service(db: Session = Depends(get_db)) -> AsisSyncService:
    return AsisSyncService(db)

@lru_cache
def get_customer_sync_service() -> CustomerSyncService:
    return CustomerSyncService(SyncState())
