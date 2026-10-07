import uuid

from sqlalchemy import select

from app.models.user_photos import UserPhotos
from app.models.users import UserRole, Users
from app.exceptions import ConflictError
from app.security import password_hasher
from app.services.base_service import CrudService

class UserService(CrudService[Users]):
    model = Users
    label = "User"
    invalid_reference_message = "Invalid company or branch reference"

    def get_all_for(self, current_user: Users, skip: int = 0, limit: int = 100) -> list[Users]:
        query = select(Users)
        if current_user.user_role == UserRole.sales or (
            current_user.user_role == UserRole.branch_manager and current_user.branch_id is None
        ):
            query = query.where(Users.user_id == current_user.user_id)
        elif current_user.user_role == UserRole.branch_manager:
            query = query.where(Users.branch_id == current_user.branch_id)
        return list(self.db.scalars(query.offset(skip).limit(limit)))

    def get_by_username(self, username: str) -> Users | None:
        return self.db.scalar(select(Users).where(Users.username == username))

    def _build(self, data) -> Users:
        if self.get_by_username(data.username):
            raise ConflictError("Username already exists")

        values = data.model_dump(exclude={"password"})
        return Users(**values, password=password_hasher.hash(data.password))

    def _prepare_update(self, user: Users, values: dict) -> dict:
        new_username = values.get("username")
        if new_username and new_username != user.username and self.get_by_username(new_username):
            raise ConflictError("Username already exists")

        if "password" in values:
            values["password"] = password_hasher.hash(values["password"])

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
