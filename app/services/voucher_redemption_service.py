from datetime import date

from fastapi import HTTPException
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError
from app.models.branches import Branches
from app.models.voucher import VoucherRedemptions, Vouchers
from app.schemas.voucher_schema import PublicRedemptionCreate
from app.utils.phone import InvalidPhoneError, normalize_phone

PHONE_UNIQUE = "uq_voucher_redemptions_phone_norm"
DUPLICATE_MESSAGE = "DUPLIKAT: nomor ini sudah pernah menukar voucher"


class VoucherRedemptionService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _available(today: date):
        """Syarat voucher boleh ditukar saat ini."""
        return (
            Vouchers.is_active.is_(True),
            Vouchers.used_count < Vouchers.quota,
            or_(Vouchers.valid_from.is_(None), Vouchers.valid_from <= today),
            or_(Vouchers.valid_until.is_(None), Vouchers.valid_until >= today),
        )

    def list_active(self) -> list[dict]:
        rows = self.db.execute(
            select(Vouchers, Branches.branch_name)
            .join(Branches, Branches.branch_id == Vouchers.branch_id)
            .where(*self._available(date.today()))
            .order_by(Branches.branch_name, Vouchers.name)
        ).all()
        return [
            {
                "voucher_id": voucher.voucher_id,
                "label": f"{branch_name} - {voucher.name}",  # label unik di dropdown form
                "remaining": voucher.quota - voucher.used_count,
            }
            for voucher, branch_name in rows
        ]

    def redeem(self, data: PublicRedemptionCreate) -> None:
        try:
            phone_norm = normalize_phone(data.phone)
        except InvalidPhoneError:
            raise BadRequestError("Nomor telepon tidak valid")

        voucher = self.db.scalar(
            select(Vouchers)
            .join(Branches, Branches.branch_id == Vouchers.branch_id)
            .where((Branches.branch_name + " - " + Vouchers.name) == data.voucher_label)
        )
        if voucher is None:
            raise BadRequestError("Voucher tidak ditemukan")

        # Cek cepat; penjaga sebenarnya tetap UNIQUE di database
        if self.db.scalar(
            select(VoucherRedemptions.redemption_id).where(
                VoucherRedemptions.phone_norm == phone_norm
            )
        ):
            raise HTTPException(409, DUPLICATE_MESSAGE)

        # Ambil jatah kuota secara atomik (aman untuk request bersamaan)
        claimed = self.db.execute(
            update(Vouchers)
            .where(Vouchers.voucher_id == voucher.voucher_id, *self._available(date.today()))
            .values(used_count=Vouchers.used_count + 1)
        ).rowcount
        if not claimed:
            self.db.rollback()
            raise HTTPException(409, "Voucher sudah tidak tersedia (kuota habis atau tidak aktif)")

        self.db.add(
            VoucherRedemptions(
                voucher_id=voucher.voucher_id,
                full_name=data.full_name,
                phone=data.phone,
                phone_norm=phone_norm,
            )
        )
        try:
            self.db.commit()  # kuota dan penukaran tersimpan dalam satu transaksi
        except IntegrityError as exc:
            self.db.rollback()  # jatah kuota ikut dibatalkan
            if PHONE_UNIQUE in str(exc.orig):
                raise HTTPException(409, DUPLICATE_MESSAGE)
            raise