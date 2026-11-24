import logging
import re
from enum import Enum

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config.config import settings
from app.models.activity_log import ActivityLogs
from app.models.users import Users

logger = logging.getLogger("app.activity")


class Action(str, Enum):
    login = "LOGIN"
    logout = "LOGOUT"
    create = "CREATE"
    update = "UPDATE"
    delete = "DELETE"
    post = "POST"
    sync = "SYNC"
    redeem = "REDEEM"


class Module(str, Enum):
    auth = "auth"
    customer = "customer"
    customer_visit = "customer_visit"
    voucher = "voucher"
    qr = "qr"
    user = "user"
    master = "master"
    asis = "asis"


class UserAgentLabel:
    BROWSERS = (
        ("Edg", "Edge"),
        ("OPR", "Opera"),
        ("Firefox", "Firefox"),
        ("Chrome", "Chrome"),
        ("Safari", "Safari"),
    )
    SYSTEMS = (
        ("iPhone", "iPhone"),
        ("iPad", "iPad"),
        ("Android", "Android"),
        ("Windows", "Windows"),
        ("Mac OS X", "macOS"),
        ("Linux", "Linux"),
    )

    @classmethod
    def describe(cls, value: str | None) -> str | None:
        if not value:
            return None
        browser = cls._browser(value)
        system = next((label for key, label in cls.SYSTEMS if key in value), None)
        if browser and system:
            return f"{browser} di {system}"
        return browser or system or value[:120]

    @classmethod
    def _browser(cls, value: str) -> str | None:
        for key, label in cls.BROWSERS:
            match = re.search(rf"{key}/(\d+)", value)
            if match:
                return f"{label} {match.group(1)}"
        return None


class ActivityLogger:
    def __init__(self, db: Session, user: Users, request: Request | None = None):
        self.db = db
        self.user = user
        self.request = request

    def created(self, module: Module, noun: str, name: str) -> None:
        self.record(Action.create, module, f'Menambah {noun} "{name}"')

    def updated(self, module: Module, noun: str, name: str) -> None:
        self.record(Action.update, module, f'Mengubah {noun} "{name}"')

    def deleted(self, module: Module, noun: str, name: str) -> None:
        self.record(Action.delete, module, f'Menghapus {noun} "{name}"')

    def restored(self, module: Module, noun: str, name: str) -> None:
        self.record(Action.update, module, f'Memulihkan {noun} "{name}"')

    def record(self, action: Action, module: Module, description: str) -> None:
        try:
            self.db.add(self._build(action, module, description))
            self.db.commit()
        except Exception:
            self.db.rollback()
            logger.exception("Failed to record activity: %s", description)

    def _build(self, action: Action, module: Module, description: str) -> ActivityLogs:
        user = self.user
        return ActivityLogs(
            user_id=user.user_id,
            user_name=f"{user.first_name} {user.last_name}".strip(),
            user_role=user.user_role.value,
            action=action.value,
            module=module.value,
            description=description,
            company_id=user.company_id,
            branch_id=user.branch_id,
            ip_address=self._client_ip(),
            user_agent=UserAgentLabel.describe(self._header("user-agent")),
        )

    def _header(self, name: str) -> str | None:
        return self.request.headers.get(name) if self.request else None

    def _client_ip(self) -> str | None:
        if self.request is None:
            return None
        if settings.trust_proxy_headers:
            first = (self._header("x-forwarded-for") or "").split(",")[0].strip()
            if first:
                return first
        return self.request.client.host if self.request.client else None
