from sqlalchemy import String, cast, func

from app.models.customer_visits import CustomerVisits
from app.models.customers import Customers
from app.models.users import Users

VISIT_BRANCH = func.coalesce(Customers.branch_id, Users.branch_id)

CUSTOMER_KEY = func.coalesce(cast(CustomerVisits.customer_id, String), CustomerVisits.phone)
