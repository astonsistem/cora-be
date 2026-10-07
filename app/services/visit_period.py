from datetime import date, datetime, time, timedelta

from app.models.customer_visits import CustomerVisits

class VisitPeriod:
    def __init__(self, date_from: date | None = None, date_to: date | None = None):
        self.date_from = date_from
        self.date_to = date_to

    def conditions(self) -> list:
        conditions = []
        if self.date_from:
            conditions.append(CustomerVisits.posted_at >= datetime.combine(self.date_from, time.min))
        if self.date_to:
            conditions.append(
                CustomerVisits.posted_at < datetime.combine(self.date_to + timedelta(days=1), time.min)
            )
        return conditions

    def apply(self, query):
        for condition in self.conditions():
            query = query.where(condition)
        return query
