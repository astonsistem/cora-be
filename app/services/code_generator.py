import secrets

UPPER_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LOWER_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


class CodeGenerator:
    def __init__(self, alphabet: str, length: int, prefix: str = ""):
        self.alphabet = alphabet
        self.length = length
        self.prefix = prefix

    @classmethod
    def for_voucher_code(cls) -> "CodeGenerator":
        return cls(UPPER_ALPHABET, 6, "CORA")

    @classmethod
    def for_voucher_definition(cls) -> "CodeGenerator":
        return cls(UPPER_ALPHABET, 8, "VCH")

    @classmethod
    def for_qr(cls) -> "CodeGenerator":
        return cls(LOWER_ALPHABET, 8)

    def next(self) -> str:
        body = "".join(secrets.choice(self.alphabet) for _ in range(self.length))
        return f"{self.prefix}-{body}" if self.prefix else body
