from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.asis_client import AsisClient, AsisGateway
from app.exceptions import BadRequestError
from app.models.branches import Branches
from app.models.category import Category
from app.models.companies import Companies


def _pick(item: dict, *keys: str):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


class BaseSyncer(ABC):
    label: str 
    fields: tuple[str, ...]

    def __init__(self, db: Session):
        self.db = db

    @abstractmethod
    def fetch(self, gateway: AsisGateway) -> list[dict]:
        """Mengambil data mentah dari ASIS."""

    @abstractmethod
    def parse(self, item: dict) -> tuple | None:
        """Mengubah satu data mentah menjadi tuple yang elemen pertamanya adalah ID ASIS (None kalau tidak valid)."""

    @abstractmethod
    def upsert(self, parsed: list[tuple], now: datetime) -> dict:
        """Menyimpan data hasil parse (tanpa commit) dan mengembalikan hitungan."""

    @abstractmethod
    def preview(self, gateway: AsisGateway) -> dict:
        """Membandingkan data ASIS dengan database tanpa menyimpan apa pun."""

    def sync(self, gateway: AsisGateway) -> dict:
        items = self.fetch(gateway)
        parsed = [p for p in map(self.parse, items) if p]
        counts = self.upsert(parsed, datetime.now())
        self.db.commit()
        return {**counts, "skipped": len(items) - len(parsed)}

    def index(self, gateway: AsisGateway) -> dict[str, tuple]:
        return {p[0]: p for p in filter(None, map(self.parse, self.fetch(gateway)))}

    def _diff(self, obj, values: dict) -> dict:
        return {
            field: {"old": getattr(obj, field), "new": values[field]}
            for field in self.fields
            if getattr(obj, field) != values[field]
        }

class CompanySyncer(BaseSyncer):
    label = "Company"
    fields = ("company_code", "company_name", "company_address")

    def fetch(self, gateway):
        return gateway.get_companies()

    def parse(self, item):
        asis_id = _pick(item, "id")
        name = _pick(item, "name")
        if asis_id is None or name is None:
            return None
        return str(asis_id), {
            "company_code": _pick(item, "companyCode", "company_code") or "",
            "company_name": name,
            "company_address": _pick(item, "address") or "",
        }

    def upsert(self, parsed, now):
        existing = {c.asis_company_id: c for c in self.db.scalars(select(Companies))}
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
                self.db.add(company)
                existing[asis_id] = company
                created += 1
        return {"created": created, "updated": updated}

    def preview(self, gateway):
        local = {c.asis_company_id: c for c in self.db.scalars(select(Companies))}
        result = {"new": [], "changed": []}
        for asis_id, values in filter(None, map(self.parse, self.fetch(gateway))):
            company = local.get(asis_id)
            if not company:
                result["new"].append({"asis_id": asis_id, **values})
                continue
            changes = self._diff(company, values)
            if changes:
                result["changed"].append(
                    {"asis_id": asis_id, "company_name": company.company_name, "changes": changes}
                )
        return result

class BranchSyncer(BaseSyncer):
    label = "Branch"
    fields = ("branch_code", "branch_name", "branch_address")

    def fetch(self, gateway):
        return gateway.get_branches()

    def parse(self, item):
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

    def upsert(self, parsed, now):
        company_ids = {c.asis_company_id: c.company_id for c in self.db.scalars(select(Companies))}
        existing = {b.asis_branch_id: b for b in self.db.scalars(select(Branches))}
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
                self.db.add(branch)
                existing[asis_id] = branch
                created += 1
        return {"created": created, "updated": updated, "without_company": without_company}

    def preview(self, gateway):
        local_companies = {c.asis_company_id for c in self.db.scalars(select(Companies))}
        local = {b.asis_branch_id: b for b in self.db.scalars(select(Branches))}
        result = {"new": [], "changed": []}
        for asis_id, asis_company_id, fields in filter(None, map(self.parse, self.fetch(gateway))):
            branch = local.get(asis_id)
            if not branch:
                result["new"].append(
                    {
                        "asis_id": asis_id,
                        "asis_company_id": asis_company_id,
                        "company_exists": asis_company_id in local_companies,
                        **fields,
                    }
                )
                continue
            changes = self._diff(branch, fields)
            if changes:
                result["changed"].append(
                    {"asis_id": asis_id, "branch_name": branch.branch_name, "changes": changes}
                )
        return result

class CategorySyncer(BaseSyncer):
    label = "Category"
    fields = ("name",)

    def fetch(self, gateway):
        return gateway.get_categories()

    def parse(self, item):
        asis_id = _pick(item, "id")
        name = _pick(item, "name")
        if asis_id is None or name is None:
            return None
        return str(asis_id), {"name": name}

    def upsert(self, parsed, now):
        existing = {}
        legacy = {} 
        for c in self.db.scalars(select(Category)):
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
                self.db.add(category)
                existing[asis_id] = category
                created += 1
        return {"created": created, "updated": updated}

    def preview(self, gateway):
        local = {c.asis_category_id: c for c in self.db.scalars(select(Category)) if c.asis_category_id}
        result = {"new": [], "changed": []}
        for asis_id, values in filter(None, map(self.parse, self.fetch(gateway))):
            category = local.get(asis_id)
            if not category:
                result["new"].append({"asis_id": asis_id, **values})
                continue
            changes = self._diff(category, values)
            if changes:
                result["changed"].append({"asis_id": asis_id, "name": category.name, "changes": changes})
        return result

class AsisSyncService:
    def __init__(self, db: Session, gateway: AsisGateway | None = None):
        self.db = db
        self._gateway = gateway
        self.companies = CompanySyncer(db)
        self.branches = BranchSyncer(db)
        self.categories = CategorySyncer(db)

    @property
    def gateway(self) -> AsisGateway:
        if self._gateway is None:
            self._gateway = AsisClient()
        return self._gateway

    def sync_all(self) -> dict:
        return {
            "companies": self.companies.sync(self.gateway),
            "branches": self.branches.sync(self.gateway),
            "categories": self.categories.sync(self.gateway),
        }

    def preview(self) -> dict:
        return {
            "companies": self.companies.preview(self.gateway),
            "branches": self.branches.preview(self.gateway),
            "categories": self.categories.preview(self.gateway),
        }

    def apply_selected(
        self,
        company_ids: list[str],
        branch_ids: list[str],
        category_ids: list[str] | None = None,
    ) -> None:
        wanted_companies = set(company_ids)
        wanted_branches = set(branch_ids)

        asis_categories = {}
        if category_ids is None or category_ids:
            asis_categories = self.categories.index(self.gateway)
        wanted_categories = set(asis_categories) if category_ids is None else set(category_ids)
        self._ensure_exist(self.categories, wanted_categories, asis_categories)

        asis_companies = self.companies.index(self.gateway) if wanted_companies else {}
        asis_branches = self.branches.index(self.gateway) if wanted_branches else {}
        self._ensure_exist(self.companies, wanted_companies, asis_companies)
        self._ensure_exist(self.branches, wanted_branches, asis_branches)

        local_company_ids = {c.asis_company_id for c in self.db.scalars(select(Companies))}
        available = local_company_ids | wanted_companies
        orphans = sorted(
            asis_id
            for asis_id in wanted_branches
            if asis_branches[asis_id][1] and asis_branches[asis_id][1] not in available
        )
        if orphans:
            raise BadRequestError(
                "Belum ada company untuk branch ini, pilih company: "
                + ", ".join(orphans)
            )

        now = datetime.now()
        self.companies.upsert([asis_companies[i] for i in sorted(wanted_companies)], now)
        self.db.flush()
        self.branches.upsert([asis_branches[i] for i in sorted(wanted_branches)], now)
        self.categories.upsert([asis_categories[i] for i in sorted(wanted_categories)], now)
        self.db.commit()

    @staticmethod
    def _ensure_exist(syncer: BaseSyncer, wanted: set[str], available: dict) -> None:
        missing = sorted(wanted - available.keys())
        if missing:
            raise BadRequestError(f"{syncer.label} tidak ditemukan di ASIS: {', '.join(missing)}")
