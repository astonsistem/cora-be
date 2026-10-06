"""Posting dari sisi Customer Visit. Posting sebenarnya dilakukan oleh customer_post_service."""
from sqlalchemy.orm import Session

from app.asis_client import AsisClient
from app.models.customer_visits import CustomerVisits
from app.services import customer_post_service, customer_service
from app.services.customer_post_service import AlreadyPostedError
from app.services.customer_post_service import PostError as VisitPostError

__all__ = ["AlreadyPostedError", "VisitPostError", "post_visit"]


def post_visit(db: Session, visit: CustomerVisits, client: AsisClient | None = None) -> CustomerVisits:
    customer = visit.customer
    if customer is None:
        # Visit lama yang dibuat sebelum ada Master Customer.
        try:
            customer = customer_service.create_from_visit(db, visit)
        except ValueError as e:
            raise VisitPostError(str(e))
        visit.customer_id = customer.customer_id
        db.flush()

    customer_post_service.post_customer(db, customer, client)
    db.refresh(visit)
    return visit
