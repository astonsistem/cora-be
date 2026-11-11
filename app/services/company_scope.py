import uuid

from sqlalchemy.orm import Session

from app.exceptions import ForbiddenError
from app.models.branches import Branches
from app.models.companies import Companies
from app.models.users import Users

class CompanyScope:
    def __init__(self, user: Users):
        self.user = user

    @property
    def restricted(self) -> bool:
        return not self.user.is_superadmin

    @property
    def company_id(self) -> uuid.UUID | None:
        if not self.restricted:
            return None
        if self.user.company_id is None:
            raise ForbiddenError("Akun Anda belum terhubung ke company")
        return self.user.company_id

    def asis_company_id(self, db: Session) -> str | None:
        company = db.get(Companies, self.company_id)
        return company.asis_company_id if company else None

    def ensure_branch(self, branch: Branches) -> None:
        if self.restricted and branch.company_id != self.company_id:
            raise ForbiddenError("Branch tersebut bukan milik company Anda")
