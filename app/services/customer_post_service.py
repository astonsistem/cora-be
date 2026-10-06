from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.asis_client import AsisClient
from app.models.customer_visits import CustomerVisits
from app.models.customers import Customers, normalize_name, normalize_phone, phones_match

PARTNER_EMAIL = "-"

class PostError(ValueError):
    """Customer belum memenuhi syarat untuk diposting ke ASIS."""

class AlreadyPostedError(PostError):
    pass

class PartnerTakenError(AlreadyPostedError):
    """Partner ASIS yang cocok sudah tertaut dengan customer lain di Master Customer."""

def build_partner_payload(customer: Customers) -> dict:
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

def find_existing_partner(client: AsisClient, customer: Customers) -> str | None:
    for item in client.find_partners(customer.branch.asis_branch_id, customer.name):
        if normalize_name(item.get("name")) != customer.name_search:
            continue
        if phones_match(normalize_phone(item.get("phone")) or None, customer.phone_norm):
            return str(item["id"])
    return None

def mark_visits_posted(db: Session, customer: Customers) -> None:
    db.execute(
        update(CustomerVisits)
        .where(CustomerVisits.customer_id == customer.customer_id)
        .values(
            is_posted_to_asis=True,
            posted_to_asis_at=customer.posted_at,
            asis_partner_id=customer.asis_partner_id,
        )
    )

def post_customer(db: Session, customer: Customers, client: AsisClient | None = None) -> tuple[Customers, bool]:
    db.refresh(customer, with_for_update=True)
    if customer.asis_partner_id:
        db.rollback()
        raise AlreadyPostedError("Customer ini sudah diposting ke ASIS")

    try:
        payload = build_partner_payload(customer)
        client = client or AsisClient()
        partner_id = find_existing_partner(client, customer)
        linked_existing = partner_id is not None
        if linked_existing:
            owner = db.scalar(
                select(Customers).where(
                    Customers.asis_partner_id == partner_id, Customers.customer_id != customer.customer_id
                )
            )
            if owner:
                raise PartnerTakenError(
                    f"Customer ini sudah terdaftar di ASIS dan tertaut dengan '{owner.name}' di Master Customer"
                )
        else:
            partner_id = client.create_partner(payload)
    except Exception:
        db.rollback()
        raise

    customer.asis_partner_id = partner_id
    customer.posted_at = datetime.now()
    mark_visits_posted(db, customer)
    db.commit()
    db.refresh(customer)
    return customer, linked_existing
