from sqlalchemy import select

from app.models.branches import Branches
from app.services.base_service import CrudService

class BranchService(CrudService[Branches]):
    model = Branches
    label = "Branch"

    def get_all_by_ids(self, branch_ids: list) -> list[Branches]:
        if not branch_ids:
            return []

        query = select(Branches).where(Branches.branch_id.in_(branch_ids))
        return list(self.db.scalars(query))

    def get_all_by_company(self, company_id) -> list[Branches]:
        query = select(Branches).where(Branches.company_id == company_id)
        return list(self.db.scalars(query))
