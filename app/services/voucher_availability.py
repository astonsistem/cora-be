from datetime import date

from sqlalchemy import case, func, update

from app.models.voucher import VoucherStatus, Vouchers


class VoucherAvailability:
    def __init__(self, today: date | None = None):
        self.today = today or date.today()

    def conditions(self) -> tuple:
        return (
            Vouchers.status == VoucherStatus.active.value,
            Vouchers.used_count < Vouchers.quota_voucher,
            Vouchers.date_started <= self.today,
            Vouchers.date_expired >= self.today,
        )

    def is_expired(self, voucher: Vouchers) -> bool:
        return voucher.date_expired < self.today

    def state(self, voucher: Vouchers) -> str:
        if voucher.status != VoucherStatus.active.value or voucher.date_started > self.today:
            return "inactive"
        if self.is_expired(voucher):
            return "expired"
        if voucher.remaining <= 0:
            return "sold_out"
        return "active"

    def take_one(self, db, voucher_id) -> bool:
        result = db.execute(
            update(Vouchers)
            .where(Vouchers.voucher_id == voucher_id, *self.conditions())
            .values(
                used_count=Vouchers.used_count + 1,
                sold_out_at=case(
                    (Vouchers.used_count + 1 >= Vouchers.quota_voucher, func.now()),
                    else_=Vouchers.sold_out_at,
                ),
            )
        )
        return result.rowcount == 1
