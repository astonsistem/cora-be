from contextlib import contextmanager
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError, ConflictError, DomainError, NotFoundError

M = TypeVar("M")


class CrudService(Generic[M]):
    model: type[M]
    label = "Data"
    invalid_reference_message = "Invalid data or reference"
    in_use_message = "{label} is still referenced by other data"

    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100) -> list[M]:
        return list(self.db.scalars(select(self.model).offset(skip).limit(limit)))

    def get_by_id(self, obj_id) -> M | None:
        return self.db.get(self.model, obj_id)

    def get_or_404(self, obj_id) -> M:
        obj = self.get_by_id(obj_id)
        if obj is None:
            raise NotFoundError(f"{self.label} not found")
        return obj

    def create(self, data) -> M:
        with self._transaction(BadRequestError(self.invalid_reference_message)):
            obj = self._build(data)
            self.db.add(obj)
            self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: M, data) -> M:
        with self._transaction(BadRequestError(self.invalid_reference_message)):
            values = self._prepare_update(obj, data.model_dump(exclude_unset=True))
            for key, value in values.items():
                setattr(obj, key, value)
            self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: M) -> None:
        with self._transaction(ConflictError(self.in_use_message.format(label=self.label))):
            self.db.delete(obj)
            self.db.commit()

    def _build(self, data) -> M:
        return self.model(**data.model_dump())

    def _prepare_update(self, obj: M, values: dict) -> dict:
        return values

    @contextmanager
    def _transaction(self, on_integrity_error: DomainError | None = None):
        try:
            yield
        except IntegrityError:
            self.db.rollback()
            if on_integrity_error is None:
                raise
            raise on_integrity_error from None
        except Exception:
            self.db.rollback()
            raise

    def _commit(self) -> None:
        with self._transaction():
            self.db.commit()
