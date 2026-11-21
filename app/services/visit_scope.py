from sqlalchemy import and_, false, or_, select, true

from app.models.customer_visits import CustomerVisits
from app.models.users import UserRole, Users
from app.models.voucher_qr import VoucherQrs

class VisitScope:
    def __init__(self, user: Users):
        self.user = user

    def user_condition(self):
        if self.user.is_superadmin:
            return true()
        own = Users.user_id == self.user.user_id
        if self.user.user_role == UserRole.sales:
            return own
        if self.user.user_role == UserRole.branch_manager:
            visible_roles = [UserRole.sales]
            in_scope = Users.branch_id == self.user.branch_id if self.user.branch_id is not None else None
        else:
            visible_roles = [UserRole.sales, UserRole.branch_manager]
            in_scope = Users.company_id == self.user.company_id if self.user.company_id is not None else None
        if in_scope is None:
            return own
        return or_(own, and_(Users.user_role.in_(visible_roles), in_scope))

    def qr_condition(self):
        if self.user.is_superadmin:
            return true()
        if self.user.user_role == UserRole.sales or self.user.company_id is None:
            return false()
        company_qrs = select(VoucherQrs.qr_id).where(VoucherQrs.company_id == self.user.company_id)
        return CustomerVisits.qr_id.in_(company_qrs)

    def apply(self, query):
        return query.outerjoin(Users, CustomerVisits.user_id == Users.user_id).where(
            or_(self.user_condition(), self.qr_condition())
        )
