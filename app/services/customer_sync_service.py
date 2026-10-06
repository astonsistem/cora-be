import threading
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.asis_client import AsisClient, PARTNER_PAGE_SIZE
from app.database import SessionLocal
from app.models.branches import Branches
from app.models.category import Category
from app.models.customers import Customers, normalize_name, normalize_phone, phones_match
from app.services.customer_post_service import mark_visits_posted

_lock = threading.Lock()
_state: dict = {"running": False}

def get_status() -> dict:
    with _lock:
        return dict(_state)

def start(branch_id: uuid.UUID | None) -> bool:
    with _lock:
        if _state.get("running"):
            return False
        _state.clear()
        _state.update(
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
            error=None,
        )
        return True


def _bump(**counts: int) -> None:
    with _lock:
        for key, value in counts.items():
            _state[key] = _state.get(key, 0) + value

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


def _sync_page(
    db: Session,
    items: list[dict],
    branch: Branches,
    categories: dict[str, uuid.UUID],
    pending: list[Customers],
    now: datetime,
) -> None:
    ids = [str(item["id"]) for item in items if item.get("id")]
    existing = {
        c.asis_partner_id: c
        for c in db.scalars(select(Customers).where(Customers.asis_partner_id.in_(ids)))
    }
    created = updated = linked = skipped = 0
    for item in items:
        fields = _item_fields(item, categories)
        if fields is None:
            skipped += 1
            continue
        partner_id = str(item["id"])

        customer = existing.get(partner_id)
        if customer:
            for key, value in fields.items():
                setattr(customer, key, value)
            customer.last_synced_at = now
            updated += 1
            continue

        name_key, phone_key = normalize_name(fields["name"]), normalize_phone(fields["phone"]) or None
        match = next(
            (c for c in pending if c.name_search == name_key and phones_match(c.phone_norm, phone_key)),
            None,
        )
        if match:
            pending.remove(match)
            for key, value in fields.items():
                if value is not None:
                    setattr(match, key, value)
            match.asis_partner_id = partner_id
            match.posted_at = now
            match.last_synced_at = now
            db.flush()
            mark_visits_posted(db, match)
            existing[partner_id] = match
            linked += 1
            continue

        customer = Customers(asis_partner_id=partner_id, branch_id=branch.branch_id, last_synced_at=now, **fields)
        db.add(customer)
        existing[partner_id] = customer
        created += 1

    db.commit()
    _bump(created=created, updated=updated, linked=linked, skipped=skipped, pages_done=1)

def _sync_branch(db: Session, client: AsisClient, branch: Branches, categories: dict[str, uuid.UUID]) -> None:
    pending = list(
        db.scalars(
            select(Customers).where(Customers.branch_id == branch.branch_id, Customers.asis_partner_id.is_(None))
        )
    )
    now = datetime.now()
    page, pages = 1, 1
    while page <= pages:
        body = client.get_partner_page(page, PARTNER_PAGE_SIZE, branch.asis_branch_id)
        pages = int(body.get("pages") or 1)
        _sync_page(db, body.get("items") or [], branch, categories, pending, now)
        page += 1

def run(branch_id: uuid.UUID | None, company_id: uuid.UUID | None) -> None:
    try:
        with SessionLocal() as db:
            query = select(Branches).where(Branches.asis_branch_id.isnot(None))
            if branch_id:
                query = query.where(Branches.branch_id == branch_id)
            elif company_id:
                query = query.where(Branches.company_id == company_id)
            branches = list(db.scalars(query.order_by(Branches.branch_name)))
            categories = {
                c.asis_category_id: c.category_id
                for c in db.scalars(select(Category).where(Category.asis_category_id.isnot(None)))
            }
            with _lock:
                _state["branches_total"] = len(branches)

            client = AsisClient()
            for branch in branches:
                _sync_branch(db, client, branch, categories)
                _bump(branches_done=1)
    except Exception as e:
        with _lock:
            _state["error"] = f"{type(e).__name__}: {e}"
    finally:
        with _lock:
            _state["running"] = False
            _state["finished_at"] = datetime.now()
