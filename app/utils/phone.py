import re


class InvalidPhoneError(ValueError):
    pass


def normalize_phone(raw: str) -> str:
    """Ubah berbagai format nomor ke format lokal berawalan 0.

    '+62 821-3861-3306' -> '082138613306'
    '0821-5438-1736'    -> '082154381736'
    '8999258971'        -> '08999258971'
    """
    digits = re.sub(r"\D", "", raw or "")

    if digits.startswith("0062"):
        digits = "0" + digits[4:]
    elif digits.startswith("62"):
        digits = "0" + digits[2:]
    elif digits.startswith("8"):
        digits = "0" + digits

    # Hanya nomor seluler: 08xx..., total 10-14 digit
    if not digits.startswith("08") or not 10 <= len(digits) <= 14:
        raise InvalidPhoneError("Format nomor telepon tidak valid")

    return digits