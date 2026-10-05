from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.asis_client import AsisClient
from app.models.branches import Branches
from app.models.category import Category
from app.models.companies import Companies

COMPANY_FIELDS = ("company_code", "company_name", "company_address")
BRANCH_FIELDS = ("branch_code", "branch_name", "branch_address")
CATEGORY_FIELDS = ("name",)

def _pick(item: dict, *keys: str):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


def _parse_company(item: dict) -> tuple[str, dict] | None:
    asis_id = _pick(item, "id")
    name = _pick(item, "name")
    if asis_id is None or name is None:
        return None
    return str(asis_id), {
        "company_code": _pick(item, "companyCode", "company_code") or "",
        "company_name": name,
        "company_address": _pick(item, "address") or "",
    }


def _parse_branch(item: dict) -> tuple[str, str | None, dict] | None:
    asis_id = _pick(item, "id")
    name = _pick(item, "name")
    if asis_id is None or name is None:
        return None

    company_data = item.get("company")
    asis_company_id = _pick(item, "company_id", "companyId") or (
        _pick(company_data, "id") if isinstance(company_data, dict) else None
    )
    return (
        str(asis_id),
        str(asis_company_id) if asis_company_id else None,
        {
            "branch_code": _pick(item, "branchCode", "branch_code") or "",
            "branch_name": name,
            "branch_address": _pick(item, "address") or "",
        },
    )


def _parse_category(item: dict) -> tuple[str, dict] | None:
    asis_id = _pick(item, "id")
    name = _pick(item, "name")
    if asis_id is None or name is None:
        return None
    return str(asis_id), {"name": name}


def _diff(obj, values: dict, fields: tuple[str, ...]) -> dict:
    return {
        field: {"old": getattr(obj, field), "new": values[field]}
        for field in fields
        if getattr(obj, field) != values[field]
    }


def _upsert_companies(db: Session, parsed: list[tuple[str, dict]], now: datetime) -> tuple[int, int]:
    existing = {c.asis_company_id: c for c in db.scalars(select(Companies))}
    created = updated = 0
    for asis_id, values in parsed:
        values = {**values, "last_synced_at": now}
        company = existing.get(asis_id)
        if company:
            for key, value in values.items():
                setattr(company, key, value)
            updated += 1
        else:
            company = Companies(asis_company_id=asis_id, **values)
            db.add(company)
            existing[asis_id] = company
            created += 1
    return created, updated


def _upsert_branches(
    db: Session, parsed: list[tuple[str, str | None, dict]], now: datetime
) -> tuple[int, int, int]:
    company_ids = {c.asis_company_id: c.company_id for c in db.scalars(select(Companies))}
    existing = {b.asis_branch_id: b for b in db.scalars(select(Branches))}
    created = updated = without_company = 0
    for asis_id, asis_company_id, fields in parsed:
        company_id = company_ids.get(asis_company_id) if asis_company_id else None
        if company_id is None:
            without_company += 1
        values = {**fields, "company_id": company_id, "last_synced_at": now}
        branch = existing.get(asis_id)
        if branch:
            for key, value in values.items():
                setattr(branch, key, value)
            updated += 1
        else:
            branch = Branches(asis_branch_id=asis_id, **values)
            db.add(branch)
            existing[asis_id] = branch
            created += 1
    return created, updated, without_company


def _upsert_categories(db: Session, parsed: list[tuple[str, dict]]) -> tuple[int, int]:
    existing = {}
    legacy = {}  # kategori lokal lama yang belum punya ID ASIS, dicocokkan lewat nama
    for c in db.scalars(select(Category)):
        if c.asis_category_id:
            existing[c.asis_category_id] = c
        else:
            legacy.setdefault(c.name.strip().lower(), c)

    created = updated = 0
    for asis_id, values in parsed:
        category = existing.get(asis_id) or legacy.pop(values["name"].strip().lower(), None)
        if category:
            category.asis_category_id = asis_id
            for key, value in values.items():
                setattr(category, key, value)
            existing[asis_id] = category
            updated += 1
        else:
            category = Category(asis_category_id=asis_id, **values)
            db.add(category)
            existing[asis_id] = category
            created += 1
    return created, updated


def sync_categories(db: Session, client: AsisClient) -> dict:
    items = client.get_categories()
    parsed = [p for p in map(_parse_category, items) if p]
    created, updated = _upsert_categories(db, parsed)
    db.commit()
    return {"created": created, "updated": updated, "skipped": len(items) - len(parsed)}


def sync_companies(db: Session, client: AsisClient) -> dict:
    items = client.get_companies()
    parsed = [p for p in map(_parse_company, items) if p]
    created, updated = _upsert_companies(db, parsed, datetime.now())
    db.commit()
    return {"created": created, "updated": updated, "skipped": len(items) - len(parsed)}


def sync_branches(db: Session, client: AsisClient) -> dict:
    items = client.get_branches()
    parsed = [p for p in map(_parse_branch, items) if p]
    created, updated, without_company = _upsert_branches(db, parsed, datetime.now())
    db.commit()
    return {
        "created": created,
        "updated": updated,
        "skipped": len(items) - len(parsed),
        "without_company": without_company,
    }


def sync_all(db: Session, client: AsisClient | None = None) -> dict:
    client = client or AsisClient()
    return {
        "companies": sync_companies(db, client),
        "branches": sync_branches(db, client),
        "categories": sync_categories(db, client),
    }


def preview(db: Session, client: AsisClient | None = None) -> dict:
    client = client or AsisClient()
    local_companies = {c.asis_company_id: c for c in db.scalars(select(Companies))}
    local_branches = {b.asis_branch_id: b for b in db.scalars(select(Branches))}

    companies = {"new": [], "changed": []}
    for asis_id, values in filter(None, map(_parse_company, client.get_companies())):
        local = local_companies.get(asis_id)
        if not local:
            companies["new"].append({"asis_id": asis_id, **values})
            continue
        changes = _diff(local, values, COMPANY_FIELDS)
        if changes:
            companies["changed"].append(
                {"asis_id": asis_id, "company_name": local.company_name, "changes": changes}
            )

    branches = {"new": [], "changed": []}
    for asis_id, asis_company_id, fields in filter(None, map(_parse_branch, client.get_branches())):
        local = local_branches.get(asis_id)
        if not local:
            branches["new"].append(
                {
                    "asis_id": asis_id,
                    "asis_company_id": asis_company_id,
                    "company_exists": asis_company_id in local_companies,
                    **fields,
                }
            )
            continue
        changes = _diff(local, fields, BRANCH_FIELDS)
        if changes:
            branches["changed"].append(
                {"asis_id": asis_id, "branch_name": local.branch_name, "changes": changes}
            )

    local_categories = {c.asis_category_id: c for c in db.scalars(select(Category)) if c.asis_category_id}
    categories = {"new": [], "changed": []}
    for asis_id, values in filter(None, map(_parse_category, client.get_categories())):
        local = local_categories.get(asis_id)
        if not local:
            categories["new"].append({"asis_id": asis_id, **values})
            continue
        changes = _diff(local, values, CATEGORY_FIELDS)
        if changes:
            categories["changed"].append({"asis_id": asis_id, "name": local.name, "changes": changes})

    return {"companies": companies, "branches": branches, "categories": categories}


def apply_selected(
    db: Session,
    company_ids: list[str],
    branch_ids: list[str],
    category_ids: list[str] | None = None,
    client: AsisClient | None = None,
) -> None:
    client = client or AsisClient()
    wanted_companies = set(company_ids)
    wanted_branches = set(branch_ids)

    asis_categories = {}
    if category_ids is None or category_ids:
        asis_categories = dict(filter(None, map(_parse_category, client.get_categories())))
    wanted_categories = set(asis_categories) if category_ids is None else set(category_ids)
    missing = sorted(wanted_categories - asis_categories.keys())
    if missing:
        raise ValueError(f"Category tidak ditemukan di ASIS: {', '.join(missing)}")

    asis_companies = {}
    if wanted_companies:
        asis_companies = dict(filter(None, map(_parse_company, client.get_companies())))
    asis_branches = {}
    if wanted_branches:
        asis_branches = {
            p[0]: p for p in filter(None, map(_parse_branch, client.get_branches()))
        }

    missing = sorted(wanted_companies - asis_companies.keys())
    if missing:
        raise ValueError(f"Company tidak ditemukan di ASIS: {', '.join(missing)}")
    missing = sorted(wanted_branches - asis_branches.keys())
    if missing:
        raise ValueError(f"Branch tidak ditemukan di ASIS: {', '.join(missing)}")

    local_company_ids = {c.asis_company_id for c in db.scalars(select(Companies))}
    available = local_company_ids | wanted_companies
    orphans = sorted(
        asis_id
        for asis_id in wanted_branches
        if asis_branches[asis_id][1] and asis_branches[asis_id][1] not in available
    )
    if orphans:
        raise ValueError(
            "Belum ada company untuk branch ini, pilih company: "
            + ", ".join(orphans)
        )

    now = datetime.now()
    _upsert_companies(db, [(i, asis_companies[i]) for i in sorted(wanted_companies)], now)
    db.flush()
    _upsert_branches(db, [asis_branches[i] for i in sorted(wanted_branches)], now)
    _upsert_categories(db, [(i, asis_categories[i]) for i in sorted(wanted_categories)])
    db.commit()
