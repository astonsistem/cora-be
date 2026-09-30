from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.asis_client import AsisClient
from app.models.branches import Branches
from app.models.companies import Companies

def _pick(item: dict, *keys: str):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None

def sync_companies(db: Session, client: AsisClient) -> dict:
    now = datetime.now()
    existing = {c.asis_company_id: c for c in db.scalars(select(Companies))}
    created = updated = skipped = 0

    for item in client.get_companies():
        asis_id = _pick(item, "id")
        name = _pick(item, "name")
        if asis_id is None or name is None:
            skipped += 1
            continue

        values = {
            "company_code": _pick(item, "companyCode", "company_code") or "",
            "company_name": name,
            "company_address": _pick(item, "address") or "",
            "last_synced_at": now,
        }
        company = existing.get(str(asis_id))
        if company:
            for key, value in values.items():
                setattr(company, key, value)
            updated += 1
        else:
            company = Companies(asis_company_id=str(asis_id), **values)
            db.add(company)
            existing[str(asis_id)] = company
            created += 1

    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped}

def sync_branches(db: Session, client: AsisClient) -> dict:
    now = datetime.now()
    company_ids = {c.asis_company_id: c.company_id for c in db.scalars(select(Companies))}
    existing = {b.asis_branch_id: b for b in db.scalars(select(Branches))}
    created = updated = skipped = without_company = 0

    for item in client.get_branches():
        asis_id = _pick(item, "id")
        name = _pick(item, "name")
        if asis_id is None or name is None:
            skipped += 1
            continue

        company_data = item.get("company")
        asis_company_id = _pick(item, "company_id", "companyId") or (
            _pick(company_data, "id") if isinstance(company_data, dict) else None
        )
        company_id = company_ids.get(str(asis_company_id)) if asis_company_id else None
        if company_id is None:
            without_company += 1

        values = {
            "company_id": company_id,
            "branch_code": _pick(item, "branchCode", "branch_code") or "",
            "branch_name": name,
            "branch_address": _pick(item, "address") or "",
            "last_synced_at": now,
        }
        branch = existing.get(str(asis_id))
        if branch:
            for key, value in values.items():
                setattr(branch, key, value)
            updated += 1
        else:
            branch = Branches(asis_branch_id=str(asis_id), **values)
            db.add(branch)
            existing[str(asis_id)] = branch
            created += 1

    db.commit()
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "without_company": without_company,
    }


def sync_all(db: Session, client: AsisClient | None = None) -> dict:
    client = client or AsisClient()
    return {
        "companies": sync_companies(db, client),
        "branches": sync_branches(db, client),
    }
