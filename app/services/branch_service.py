from sqlalchemy import select

from app.exceptions import NotFoundError
from app.models.branches import Branches
from app.models.users import UserRole, Users
from app.services.base_service import CrudService

class BranchService(CrudService[Branches]):
    model = Branches
    label = "Branch"

    def get_all_for(self, current_user: Users, skip: int = 0, limit: int = 100) -> list[Branches]:
        if current_user.user_role == UserRole.operasional_manager:
            return self.get_all(skip=skip, limit=limit)
        return self.get_all_by_ids([current_user.branch_id] if current_user.branch_id else [])

    def get_for_or_404(self, current_user: Users, branch_id) -> Branches:
        if current_user.user_role != UserRole.operasional_manager and branch_id != current_user.branch_id:
            raise NotFoundError(f"{self.label} not found")
        return self.get_or_404(branch_id)

    def get_all_by_ids(self, branch_ids: list) -> list[Branches]:
        if not branch_ids:
            return []

        query = select(Branches).where(Branches.branch_id.in_(branch_ids))
        return list(self.db.scalars(query))

    def get_all_by_company(self, company_id) -> list[Branches]:
        query = select(Branches).where(Branches.company_id == company_id)
        return list(self.db.scalars(query))
