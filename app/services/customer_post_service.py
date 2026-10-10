from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.asis_client import AsisClient, AsisGateway
from app.exceptions import BadRequestError
from app.models.customer_visits import CustomerVisits
from app.models.customers import Customers, normalize_name, normalize_phone, phones_match

PARTNER_EMAIL = "-"

class PostError(BadRequestError):
    """Customer belum memenuhi syarat untuk diposting ke ASIS."""

class AlreadyPostedError(PostError):
    status_code = 409
    pass

class PartnerTakenError(AlreadyPostedError):
    """Partner ASIS yang cocok sudah tertaut dengan customer lain di Master Customer."""


class CustomerPostService:
    """Mendaftarkan customer ke ASIS, atau menautkannya kalau sudah ada di sana."""

    def __init__(self, db: Session, gateway: AsisGateway | None = None):
        self.db = db
        self._gateway = gateway

    @property
    def gateway(self) -> AsisGateway:
        # Dibuat saat pertama dipakai, supaya request yang gagal validasi lokal tidak menyentuh ASIS.
        if self._gateway is None:
            self._gateway = AsisClient()
        return self._gateway

    @staticmethod
    def build_payload(customer: Customers) -> dict:
        branch = customer.branch
        if branch is None or not branch.asis_branch_id:
            raise PostError("Branch customer belum tersinkron dengan ASIS")

        category = customer.category
        if category is None or not category.asis_category_id:
            raise PostError("Category customer belum tersinkron dengan ASIS, jalankan Sync ASIS terlebih dahulu")

        return {
            "branch_id": branch.asis_branch_id,
            "partner_category_id": category.asis_category_id,
            "name": customer.name,
            "email": PARTNER_EMAIL,
            "phone": customer.phone,
            "isVendor": False,
            "isCustomer": True,
            "isInternal": False,
        }

    def find_existing_partner(self, customer: Customers) -> str | None:
        """Cari customer yang sama di ASIS: branch sama, nama sama, dan nomor telepon cocok."""
        for item in self.gateway.find_partners(customer.branch.asis_branch_id, customer.name):
            if normalize_name(item.get("name")) != customer.name_search:
                continue
            if phones_match(normalize_phone(item.get("phone")) or None, customer.phone_norm):
                return str(item["id"])
        return None

    def mark_visits_posted(self, customer: Customers) -> None:
        """Visit milik customer ikut berstatus posted."""
        self.db.execute(
            update(CustomerVisits)
            .where(CustomerVisits.customer_id == customer.customer_id)
            .values(
                is_posted_to_asis=True,
                posted_to_asis_at=customer.posted_at,
                asis_partner_id=customer.asis_partner_id,
            )
        )

    def mark_visits_unposted(self, customer: Customers) -> None:
        self.db.execute(
            update(CustomerVisits)
            .where(CustomerVisits.customer_id == customer.customer_id)
            .values(is_posted_to_asis=False, posted_to_asis_at=None, asis_partner_id=None)
        )

    def post(self, customer: Customers) -> tuple[Customers, bool]:
        """Daftarkan customer ke ASIS. Mengembalikan (customer, linked_existing)."""
        # Kunci baris supaya klik ganda tidak membuat dua partner di ASIS.
        self.db.refresh(customer, with_for_update=True)
        if customer.is_posted:
            self.db.rollback()
            raise AlreadyPostedError("Customer ini sudah diposting ke ASIS")

        try:
            payload = self.build_payload(customer)
            partner_id = self.find_existing_partner(customer)
            linked_existing = partner_id is not None
            if linked_existing:
                self._ensure_partner_not_taken(customer, partner_id)
            else:
                partner_id = self.gateway.create_partner(payload)
        except Exception:
            self.db.rollback()
            raise

        customer.mark_posted(partner_id)
        self.mark_visits_posted(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer, linked_existing

    def _ensure_partner_not_taken(self, customer: Customers, partner_id: str) -> None:
        owner = self.db.scalar(
            select(Customers).where(
                Customers.asis_partner_id == partner_id, Customers.customer_id != customer.customer_id
            )
        )
        if owner:
            raise PartnerTakenError(
                f"Customer ini sudah terdaftar di ASIS dan tertaut dengan '{owner.name}' di Master Customer"
            )
