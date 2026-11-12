from datetime import datetime

from sqlalchemy import Column, DateTime, func, inspect, select

from app.exceptions import NotFoundError


class SoftDeleteMixin:
    deleted_at = Column(DateTime, nullable=True, index=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self, when: datetime | None = None) -> None:
        self.deleted_at = when or datetime.now()

    def restore(self) -> None:
        self.deleted_at = None


class SoftDeleteServiceMixin:
    search_column = "name"

    def _active(self):
        return select(self.model).where(self.model.deleted_at.is_(None))

    def _trashed(self, q: str | None = None):
        query = select(self.model).where(self.model.deleted_at.isnot(None))
        if q and q.strip():
            column = getattr(self.model, self.search_column)
            query = query.where(column.icontains(q.strip(), autoescape=True))
        return query

    def get_by_id(self, obj_id):
        primary_key = inspect(self.model).primary_key[0]
        return self.db.scalar(self._active().where(primary_key == obj_id))

    def get_all(self, skip: int = 0, limit: int = 100):
        query = self._active().offset(skip).limit(limit)
        return list(self.db.scalars(query))

    def get_deleted(self, skip: int = 0, limit: int = 50, q: str | None = None):
        query = self._trashed(q).order_by(self.model.deleted_at.desc())
        query = query.offset(skip).limit(min(max(limit, 1), 200))
        return list(self.db.scalars(query))

    def count_deleted(self, q: str | None = None) -> int:
        subquery = self._trashed(q).subquery()
        return self.db.scalar(select(func.count()).select_from(subquery)) or 0

    def get_deleted_or_404(self, obj_id):
        primary_key = inspect(self.model).primary_key[0]
        obj = self.db.scalar(self._trashed().where(primary_key == obj_id))
        if obj is None:
            raise NotFoundError(f"{self.label} yang dihapus tidak ditemukan")
        return obj

    def delete(self, obj) -> None:
        obj.soft_delete()
        self._commit()

    def restore(self, obj):
        obj.restore()
        self._commit()
        self.db.refresh(obj)
        return obj