from sqlalchemy import String, cast, func, select

from app.models.customer_visits import CustomerVisits
from app.models.customers import Customers
from app.models.users import Users
from app.models.voucher_qr import VoucherQrs

QR_BRANCH = select(VoucherQrs.branch_id).where(VoucherQrs.qr_id == CustomerVisits.qr_id).scalar_subquery()

VISIT_BRANCH = func.coalesce(Customers.branch_id, Users.branch_id, QR_BRANCH)

CUSTOMER_KEY = func.coalesce(cast(CustomerVisits.customer_id, String), CustomerVisits.phone)
