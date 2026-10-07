from sqlalchemy import and_, or_

from app.models.customer_visits import CustomerVisits
from app.models.users import UserRole, Users

class VisitScope:
    def __init__(self, user: Users):
        self.user = user

    def user_condition(self):
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

    def apply(self, query):
        return query.join(Users, CustomerVisits.user_id == Users.user_id).where(self.user_condition())
