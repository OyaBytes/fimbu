from litestar.datastructures import MutableScopeHeaders
from litestar.middleware.base import AbstractMiddleware
from litestar.types import ASGIApp, Receive, Scope, Send


class XForwardedHostMiddleware(AbstractMiddleware):
    def __init__(self, app: ASGIApp, trusted_hosts: str | list[str] = "127.0.0.1"):
        self.app = app
        if isinstance(trusted_hosts, str):
            self.trusted_hosts = {item.strip() for item in trusted_hosts.split(",")}
        else:
            self.trusted_hosts = set(trusted_hosts)
        self.always_trust = "*" in self.trusted_hosts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            client_addr: tuple[str, int] | None = scope.get("client")
            client_host = client_addr[0] if client_addr else None

            if self.always_trust or client_host in self.trusted_hosts:
                headers = MutableScopeHeaders(scope=scope)

                if "x-forwarded-host" in headers:
                    headers.update({"host": headers["x-forwarded-host"]})
                    scope["headers"] = headers.raw

        return await self.app(scope, receive, send)
