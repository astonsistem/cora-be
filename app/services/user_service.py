import uuid

from sqlalchemy import select

from app.models.branches import Branches
from app.models.user_photos import UserPhotos
from app.models.users import UserRole, Users
from app.exceptions import ConflictError, ForbiddenError
from app.core.security.security import password_hasher
from app.schemas.user_schema import UserCreate, UserUpdate
from app.services.base_service import CrudService
from app.services.company_scope import CompanyScope

class UserService(CrudService[Users]):
    model = Users
    label = "User"
    invalid_reference_message = "Invalid company or branch reference"

    def get_all_for(
        self,
        current_user: Users,
        skip: int = 0,
        limit: int = 100,
        role: UserRole | None = None,
    ) -> list[Users]:
        query = select(Users).order_by(Users.first_name, Users.last_name, Users.user_id)
        if role is not None:
            query = query.where(Users.user_role == role)
        if current_user.user_role == UserRole.sales or (
            current_user.user_role == UserRole.branch_manager and current_user.branch_id is None
        ):
            query = query.where(Users.user_id == current_user.user_id)
        elif current_user.user_role == UserRole.branch_manager:
            query = query.where(Users.branch_id == current_user.branch_id)
        elif not current_user.is_superadmin:
            query = query.where(Users.company_id == CompanyScope(current_user).company_id)
        return list(self.db.scalars(query.offset(skip).limit(limit)))

    @staticmethod
    def ensure_can_manage(actor: Users, target_role: UserRole | None, current_role: UserRole | None = None) -> None:
        if actor.is_superadmin:
            return
        if UserRole.superadmin in (target_role, current_role):
            raise ForbiddenError("Only a superadmin can manage superadmin accounts")

    def get_for(self, actor: Users, user_id: uuid.UUID) -> Users:
        user = self.get_or_404(user_id)
        if user.user_id != actor.user_id:
            self._ensure_in_scope(actor, user)
        return user

    def create_as(self, actor: Users, data: UserCreate) -> Users:
        self.ensure_can_manage(actor, data.user_role)
        company_id = self._scoped_company(actor, data.company_id, data.branch_id)
        return self.create(data.model_copy(update={"company_id": company_id}))

    def update_as(self, actor: Users, user: Users, data: UserUpdate) -> Users:
        self.ensure_can_manage(actor, data.user_role, user.user_role)
        self._ensure_in_scope(actor, user)
        fields = data.model_fields_set
        if "company_id" in fields or "branch_id" in fields:
            company_id = data.company_id if "company_id" in fields else user.company_id
            branch_id = data.branch_id if "branch_id" in fields else user.branch_id
            scoped = self._scoped_company(actor, company_id, branch_id)
            if "company_id" in fields:
                data = data.model_copy(update={"company_id": scoped})
        return self.update(user, data)

    def delete_as(self, actor: Users, user: Users) -> None:
        self.ensure_can_manage(actor, None, user.user_role)
        self._ensure_in_scope(actor, user)
        self.delete(user)

    def _ensure_in_scope(self, actor: Users, user: Users) -> None:
        scope = CompanyScope(actor)
        if scope.restricted and user.company_id != scope.company_id:
            raise ForbiddenError("User tersebut bukan milik company Anda")

    def _scoped_company(self, actor: Users, company_id: uuid.UUID | None, branch_id: uuid.UUID | None):
        scope = CompanyScope(actor)
        if not scope.restricted:
            return company_id
        if company_id not in (None, scope.company_id):
            raise ForbiddenError("Anda hanya dapat mengelola user di company Anda")
        if branch_id is not None:
            branch = self.db.get(Branches, branch_id)
            if branch is None or branch.company_id != scope.company_id:
                raise ForbiddenError("Branch tersebut bukan milik company Anda")
        return scope.company_id

    def get_by_username(self, username: str) -> Users | None:
        return self.db.scalar(select(Users).where(Users.username == username))

    def _build(self, data) -> Users:
        if self.get_by_username(data.username):
            raise ConflictError("Username already exists")

        values = data.model_dump(exclude={"password"})
        if data.user_role == UserRole.superadmin:
            values.update(company_id=None, branch_id=None)
        return Users(**values, password=password_hasher.hash(data.password))

    def _prepare_update(self, user: Users, values: dict) -> dict:
        new_username = values.get("username")
        if new_username and new_username != user.username and self.get_by_username(new_username):
            raise ConflictError("Username already exists")

        if "password" in values:
            values["password"] = password_hasher.hash(values["password"])

        if values.get("user_role", user.user_role) == UserRole.superadmin:
            values.update(company_id=None, branch_id=None)

        return values

    def get_photo(self, user_id: uuid.UUID) -> UserPhotos | None:
        return self.db.get(UserPhotos, user_id)

    def save_photo(self, user: Users, content_type: str, data: bytes) -> Users:
        photo = self.get_photo(user.user_id)
        if photo:
            photo.content_type = content_type
            photo.data = data
        else:
            self.db.add(UserPhotos(user_id=user.user_id, content_type=content_type, data=data))
        user.photo_url = f"/users/{user.user_id}/photo"
        self._commit()
        self.db.refresh(user)
        return user

    def delete_photo(self, user: Users) -> None:
        photo = self.get_photo(user.user_id)
        if photo:
            self.db.delete(photo)
        user.photo_url = None
        self._commit()
