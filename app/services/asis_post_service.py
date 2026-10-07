from sqlalchemy.orm import Session

from app.asis_client import AsisGateway
from app.models.customer_visits import CustomerVisits
from app.models.users import Users
from app.services.customer_post_service import AlreadyPostedError, CustomerPostService
from app.services.customer_post_service import PostError as VisitPostError
from app.services.customer_service import CustomerService

__all__ = ["AlreadyPostedError", "VisitPostError", "post_visit"]

def post_visit(
    db: Session,
    visit: CustomerVisits,
    current_user: Users,
    gateway: AsisGateway | None = None,
) -> CustomerVisits:
    customer = visit.customer
    if customer is None:
        customer = CustomerService(db, current_user).create_from_visit(visit)
        visit.customer_id = customer.customer_id
        db.flush()

    CustomerPostService(db, gateway).post(customer)
    db.refresh(visit)
    return visit
