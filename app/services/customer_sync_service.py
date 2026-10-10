import threading
import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.asis_client import AsisClient, AsisGateway, PARTNER_PAGE_SIZE
from app.database import SessionLocal
from app.models.branches import Branches
from app.models.category import Category
from app.models.customers import Customers, normalize_name, normalize_phone, phones_match
from app.services.customer_post_service import CustomerPostService


class SyncState:
    """Status sync yang aman dipakai dari beberapa thread.

    Disimpan di memori proses ini. Cukup untuk satu proses uvicorn; kalau BE
    dijalankan dengan beberapa worker, status tidak dibagi antar worker.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._data: dict = {"running": False}

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._data)

    def begin(self, branch_id: uuid.UUID | None) -> bool:
        """Tandai sync dimulai. Mengembalikan False kalau masih ada sync yang berjalan."""
        with self._lock:
            if self._data.get("running"):
                return False
            self._data = dict(
                running=True,
                started_at=datetime.now(),
                finished_at=None,
                branch_id=str(branch_id) if branch_id else None,
                branches_total=0,
                branches_done=0,
                pages_done=0,
                created=0,
                updated=0,
                linked=0,
                skipped=0,
                missing=0,
                warnings=[],
                error=None,
            )
            return True

    def set(self, **values) -> None:
        with self._lock:
            self._data.update(values)

    def bump(self, **counts: int) -> None:
        with self._lock:
            for key, value in counts.items():
                self._data[key] = self._data.get(key, 0) + value

    def warn(self, message: str) -> None:
        with self._lock:
            self._data["warnings"] = [*self._data.get("warnings", []), message]

    def finish(self, error: str | None = None) -> None:
        with self._lock:
            if error:
                self._data["error"] = error
            self._data["running"] = False
            self._data["finished_at"] = datetime.now()


class CustomerSyncService:
    """Menarik customer dari ASIS ke Master Customer (berjalan di background)."""

    def __init__(
        self,
        state: SyncState,
        session_factory: sessionmaker = SessionLocal,
        gateway_factory=AsisClient,
    ):
        self.state = state
        self._session_factory = session_factory
        self._gateway_factory = gateway_factory

    MISSING_GUARD_RATIO = 0.5
    MISSING_GUARD_MIN_CUSTOMERS = 10

    def status(self) -> dict:
        return self.state.snapshot()

    def start(self, branch_id: uuid.UUID | None) -> bool:
        return self.state.begin(branch_id)

    def run(self, branch_id: uuid.UUID | None, company_id: uuid.UUID | None) -> None:
        """Dipanggil sebagai background task setelah start() berhasil."""
        error = None
        try:
            with self._session_factory() as db:
                branches = self._target_branches(db, branch_id, company_id)
                categories = {
                    c.asis_category_id: c.category_id
                    for c in db.scalars(select(Category).where(Category.asis_category_id.isnot(None)))
                }
                self.state.set(branches_total=len(branches))

                gateway = self._gateway_factory()
                for branch in branches:
                    self._sync_branch(db, gateway, branch, categories)
                    self.state.bump(branches_done=1)
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
        finally:
            self.state.finish(error)

    @staticmethod
    def _target_branches(db: Session, branch_id: uuid.UUID | None, company_id: uuid.UUID | None) -> list[Branches]:
        query = select(Branches).where(Branches.asis_branch_id.isnot(None))
        if branch_id:
            query = query.where(Branches.branch_id == branch_id)
        elif company_id:
            query = query.where(Branches.company_id == company_id)
        return list(db.scalars(query.order_by(Branches.branch_name)))

    def _sync_branch(
        self,
        db: Session,
        gateway: AsisGateway,
        branch: Branches,
        categories: dict[str, uuid.UUID],
    ) -> None:
        pending = list(
            db.scalars(
                select(Customers).where(
                    Customers.branch_id == branch.branch_id,
                    Customers.asis_partner_id.is_(None),
                    Customers.deleted_at.is_(None),
                )
            )
        )
        now = datetime.now()
        page, pages, seen = 1, 1, 0
        while page <= pages:
            body = gateway.get_partner_page(page, PARTNER_PAGE_SIZE, branch.asis_branch_id)
            pages = int(body.get("pages") or 1)
            seen += self._sync_page(db, body.get("items") or [], branch, categories, pending, now)
            page += 1
        self._return_missing_to_pending(db, branch, now, seen)

    def _return_missing_to_pending(self, db: Session, branch: Branches, started_at: datetime, seen: int) -> None:
        posted_filter = (
            Customers.branch_id == branch.branch_id,
            Customers.asis_partner_id.isnot(None),
            Customers.deleted_at.is_(None),
        )
        posted_total = db.scalar(select(func.count()).select_from(Customers).where(*posted_filter)) or 0
        candidates = list(
            db.scalars(
                select(Customers).where(
                    *posted_filter,
                    or_(Customers.last_synced_at.is_(None), Customers.last_synced_at < started_at),
                    or_(Customers.posted_at.is_(None), Customers.posted_at < started_at),
                )
            )
        )
        if not candidates:
            return
        if seen == 0:
            self.state.warn(f"{branch.branch_name}: ASIS tidak mengembalikan customer, pengembalian ke pending dilewati")
            return
        too_many = (
            posted_total >= self.MISSING_GUARD_MIN_CUSTOMERS
            and len(candidates) / posted_total > self.MISSING_GUARD_RATIO
        )
        if too_many:
            self.state.warn(
                f"{branch.branch_name}: {len(candidates)} dari {posted_total} customer tidak ditemukan di ASIS, "
                "pengembalian ke pending dilewati karena hasilnya mencurigakan"
            )
            return
        post_service = CustomerPostService(db)
        for customer in candidates:
            customer.mark_unposted()
            db.flush()
            post_service.mark_visits_unposted(customer)
        db.commit()
        self.state.bump(missing=len(candidates))

    def _sync_page(
        self,
        db: Session,
        items: list[dict],
        branch: Branches,
        categories: dict[str, uuid.UUID],
        pending: list[Customers],
        now: datetime,
    ) -> int:
        ids = [str(item["id"]) for item in items if item.get("id")]
        existing = {
            c.asis_partner_id: c
            for c in db.scalars(select(Customers).where(Customers.asis_partner_id.in_(ids)))
        }
        post_service = CustomerPostService(db)
        created = updated = linked = skipped = 0
        for item in items:
            fields = self._item_fields(item, categories)
            if fields is None:
                skipped += 1
                continue
            partner_id = str(item["id"])

            customer = existing.get(partner_id)
            if customer and customer.is_deleted:
                skipped += 1
                continue
            if customer:
                for key, value in fields.items():
                    setattr(customer, key, value)
                customer.last_synced_at = now
                updated += 1
                continue

            # Customer yang sebelumnya didaftarkan dari CORA dan ternyata sudah ada di ASIS: tautkan.
            match = self._find_pending_match(pending, fields)
            if match:
                pending.remove(match)
                for key, value in fields.items():
                    if value is not None:
                        setattr(match, key, value)
                match.mark_posted(partner_id, now)
                match.last_synced_at = now
                db.flush()
                post_service.mark_visits_posted(match)
                existing[partner_id] = match
                linked += 1
                continue

            customer = Customers(asis_partner_id=partner_id, branch_id=branch.branch_id, last_synced_at=now, **fields)
            db.add(customer)
            existing[partner_id] = customer
            created += 1

        db.commit()
        self.state.bump(created=created, updated=updated, linked=linked, skipped=skipped, pages_done=1)
        return created + updated + linked

    @staticmethod
    def _item_fields(item: dict, categories: dict[str, uuid.UUID]) -> dict | None:
        name = (item.get("name") or "").strip()
        if not item.get("id") or not name:
            return None
        return {
            "name": name,
            "phone": (item.get("phone") or "").strip() or None,
            "email": (item.get("email") or "").strip() or None,
            "category_id": categories.get(str(item.get("partner_category_id"))),
        }

    @staticmethod
    def _find_pending_match(pending: list[Customers], fields: dict) -> Customers | None:
        name_key = normalize_name(fields["name"])
        phone_key = normalize_phone(fields["phone"]) or None
        return next(
            (c for c in pending if c.name_search == name_key and phones_match(c.phone_norm, phone_key)),
            None,
        )
