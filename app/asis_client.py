import os
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv

load_dotenv()

LOGIN_PATH = "/auth/login"
COMPANY_PATH = "/super/company/company"
BRANCH_PATH = "/super/branch/branch"
CATEGORY_PATH = "/company/partner_category/dropdown"
PARTNER_PATH = "/company/partner"
PARTNER_PAGE_SIZE = 100
CONNECT_TIMEOUT = 5
CONNECT_RETRIES = 3

class AsisError(Exception):
    pass

def _error_detail(res: httpx.Response) -> str:
    try:
        body = res.json()
        detail = body.get("detail") or body.get("message") if isinstance(body, dict) else None
    except ValueError:
        detail = None
    return f" - {str(detail)[:200]}" if detail else ""

def extract_items(body) -> list[dict]:
    if isinstance(body, list):
        return body
    if not isinstance(body, dict):
        return []
    if isinstance(body.get("items"), list):
        return body["items"]
    data = body.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return data["items"]
    return []

class AsisClient:
    def __init__(self):
        base_url = os.getenv("ASIS_BASE_URL")
        if not base_url:
            raise AsisError("ASIS_BASE_URL belum diisi di .env")
        self.api_url = base_url.rstrip("/")
        self.login_url = f"{self.api_url}{LOGIN_PATH}"
        self.username = os.getenv("ASIS_USERNAME")
        self.password = os.getenv("ASIS_PASSWORD")
        self._token = None
        self._http = httpx.Client(
            transport=httpx.HTTPTransport(retries=CONNECT_RETRIES),
            timeout=httpx.Timeout(30, connect=CONNECT_TIMEOUT),
        )

    def login(self) -> str:
        res = self._http.post(
            self.login_url,
            data={"grant_type": "password", "username": self.username, "password": self.password},
        )
        if res.status_code >= 400:
            raise AsisError(f"Login gagal: HTTP {res.status_code}")
        body = res.json()
        token = body.get("access_token") or body.get("token") or (body.get("data") or {}).get("access_token")
        if not token:
            raise AsisError("Token tidak ditemukan di respons login")
        self._token = token
        return token

    def _get(self, path: str):
        for attempt in (1, 2):
            if not self._token:
                self.login()
            res = self._http.get(
                f"{self.api_url}/{path.lstrip('/')}",
                headers={"Authorization": f"Bearer {self._token}", "Accept": "application/json"},
            )
            if res.status_code == 401 and attempt == 1:
                self._token = None
                continue
            if res.status_code >= 400:
                raise AsisError(f"GET {path} gagal: HTTP {res.status_code}")
            return res.json()

    def _post(self, path: str, payload: dict):
        for attempt in (1, 2):
            if not self._token:
                self.login()
            res = self._http.post(
                f"{self.api_url}/{path.lstrip('/')}",
                json=payload,
                headers={"Authorization": f"Bearer {self._token}", "Accept": "application/json"},
            )
            if res.status_code == 401 and attempt == 1:
                self._token = None
                continue
            if res.status_code >= 400:
                raise AsisError(f"POST {path} gagal: HTTP {res.status_code}{_error_detail(res)}")
            return res.json()

    def create_partner(self, payload: dict) -> str:
        body = self._post(PARTNER_PATH, payload)
        status = body.get("status") if isinstance(body, dict) else None
        if status is not None and not str(status).startswith("2"):
            raise AsisError(f"POST {PARTNER_PATH} gagal: status {status} - {body.get('message')}")
        partner_id = ((body.get("data") or {}) if isinstance(body, dict) else {}).get("id")
        if not partner_id:
            raise AsisError("ID partner tidak ditemukan di respons ASIS")
        return str(partner_id)

    def get_partner_page(
        self,
        page: int = 1,
        size: int = PARTNER_PAGE_SIZE,
        branch_asis_id: str | None = None,
        name: str | None = None,
    ) -> dict:
        params = {"page": page, "size": size, "isCustomer": "true"}
        if branch_asis_id:
            params["branch_id"] = branch_asis_id
        if name:
            params["name"] = name
        body = self._get(f"{PARTNER_PATH}?{urlencode(params)}")
        return body if isinstance(body, dict) else {"items": extract_items(body), "pages": 1}

    def find_partners(self, branch_asis_id: str, name: str) -> list[dict]:
        return extract_items(self.get_partner_page(1, PARTNER_PAGE_SIZE, branch_asis_id, name))

    def get_companies(self) -> list[dict]:
        return extract_items(self._get(COMPANY_PATH))

    def get_branches(self) -> list[dict]:
        return extract_items(self._get(BRANCH_PATH))

    def get_categories(self) -> list[dict]:
        return extract_items(self._get(CATEGORY_PATH))
