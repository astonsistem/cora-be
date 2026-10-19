import functools
import inspect
from typing import Any, Callable, Generic, TypeVar

from fastapi import APIRouter, Response
from fastapi.datastructures import Default, DefaultPlaceholder
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str
    data: T | None = None

class ResponseMessages:
    DEFAULTS = {
        "GET": "Data retrieved successfully",
        "POST": "Data created successfully",
        "PUT": "Data updated successfully",
        "PATCH": "Data updated successfully",
        "DELETE": "Data deleted successfully",
    }
    FALLBACK = "Request processed successfully"
    CUSTOM = {
        ("POST", "/auth/login"): "Login successful",
        ("POST", "/auth/refresh"): "Token refreshed successfully",
        ("GET", "/auth/me"): "Profile retrieved successfully",
        ("PUT", "/users/{user_id}/photo"): "Photo uploaded successfully",
        ("DELETE", "/users/{user_id}/photo"): "Photo deleted successfully",
        ("POST", "/asis/sync"): "ASIS data synced successfully",
        ("GET", "/asis/preview"): "ASIS preview retrieved successfully",
        ("POST", "/asis/apply"): "ASIS data applied successfully",
        ("POST", "/customers/sync"): "Customer sync started",
        ("GET", "/customers/sync/status"): "Customer sync status retrieved successfully",
        ("GET", "/customers/deleted"): "Deleted customers retrieved successfully",
        ("POST", "/customers/{customer_id}/restore"): "Customer restored successfully",
        ("DELETE", "/customers/{customer_id}"): "Customer deleted successfully",
        ("POST", "/customers/{customer_id}/post-to-asis"): "Customer posted to ASIS successfully",
        ("POST", "/customer-visits/{visit_id}/post-to-asis"): "Customer visit posted to ASIS successfully",
        ("GET", "/customer-visits/summary"): "Customer visit summary retrieved successfully",
        ("GET", "/public/customer-visits/count"): "Customer visit count retrieved successfully",
    }

    @classmethod
    def resolve(cls, method: str, path: str, status_code: int | None) -> str:
        custom = cls.CUSTOM.get((method, path))
        if custom:
            return custom
        if method == "POST" and status_code != 201:
            return cls.FALLBACK
        return cls.DEFAULTS.get(method, cls.FALLBACK)

class EnvelopeRoute(APIRoute):
    MARKER = "_enveloped"

    def __init__(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        response_model: Any = Default(None),
        status_code: int | None = None,
        response_class: Any = Default(JSONResponse),
        methods: Any = None,
        **kwargs: Any,
    ):
        if getattr(endpoint, self.MARKER, False) or not self._is_json(response_class):
            super().__init__(
                path,
                endpoint,
                response_model=response_model,
                status_code=status_code,
                response_class=response_class,
                methods=methods,
                **kwargs,
            )
            return

        method = next(iter(methods or ["GET"])).upper()
        message = ResponseMessages.resolve(method, path, status_code)
        inner = None if isinstance(response_model, DefaultPlaceholder) else response_model
        super().__init__(
            path,
            self._wrap(endpoint, message),
            response_model=ApiResponse[inner] if inner is not None else ApiResponse[Any],
            status_code=200 if status_code == 204 else status_code,
            response_class=response_class,
            methods=methods,
            **kwargs,
        )

    @staticmethod
    def _is_json(response_class: Any) -> bool:
        value = response_class.value if isinstance(response_class, DefaultPlaceholder) else response_class
        return inspect.isclass(value) and issubclass(value, JSONResponse)

    @classmethod
    def _wrap(cls, endpoint: Callable[..., Any], message: str) -> Callable[..., Any]:
        def envelope(result: Any) -> Any:
            if isinstance(result, Response):
                return result
            return {"success": True, "message": message, "data": result}

        if inspect.iscoroutinefunction(endpoint):
            @functools.wraps(endpoint)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                return envelope(await endpoint(*args, **kwargs))
        else:
            @functools.wraps(endpoint)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                return envelope(endpoint(*args, **kwargs))

        setattr(wrapper, cls.MARKER, True)
        return wrapper

class ApiRouter(APIRouter):
    def __init__(self, *args: Any, **kwargs: Any):
        kwargs.setdefault("route_class", EnvelopeRoute)
        super().__init__(*args, **kwargs)
