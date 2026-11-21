class DomainError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail

class BadRequestError(DomainError):
    status_code = 400

class ForbiddenError(DomainError):
    status_code = 403

class NotFoundError(DomainError):
    status_code = 404

class ConflictError(DomainError):
    status_code = 409

class UnauthorizedError(DomainError):
    status_code = 401

class TooManyRequestsError(DomainError):
    status_code = 429

    def __init__(self, retry_after: int):
        super().__init__(f"Terlalu banyak percobaan. Coba lagi dalam {retry_after} detik.")
        self.retry_after = retry_after

class PayloadTooLargeError(DomainError):
    status_code = 413

class UnsupportedMediaError(DomainError):
    status_code = 415
