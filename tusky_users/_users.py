from typing import (
    Type,
    Union,
    TypeVar,
    Iterable,
    AsyncIterable,
    Mapping,
    Any,
    Coroutine,
    Dict,
    Sequence,
    Tuple,
)

import httpx

try:
    from pydantic import (
        SecretStr,
        HttpUrl,
        EmailStr,
        dataclasses,
    )
except ImportError:
    SecretStr = str
    HttpUrl = str
    import dataclasses
# Check if pydantic[email] works
try:
    EmailStr().validate("example@tusky.org")
except ImportError:
    EmailStr = str
try:
    from tusky_snowflake import Snowflake
except ImportError:
    Snowflake = int


T = TypeVar("T")
# The type annotation for @classmethod and context managers here follows PEP 484
# https://www.python.org/dev/peps/pep-0484/#annotating-instance-and-class-methods
U = TypeVar("U", bound="BaseClient")
# An aside: I recently realized the letter "U" is used for TypeVars
# because it comes after "T" in the alphabet :P


class NotSet:
    # Todo: make borg-singleton
    pass


not_set = NotSet()


def create_body(*pairs: Tuple[Any, Any]) -> Dict:
    return {k: v for k, v in pairs if type(v) is not NotSet}


# Helper function for JWTs
def jwt_to_auth_headers(jwt: "JWT") -> Dict[str, str]:
    return {"Authorization": f"Bearer {jwt}"}


ClientType = Union[Type[httpx.Client], Type[httpx.AsyncClient]]
# https://github.com/encode/httpx/blob/ab64f7c41fc0fbe638dd586fecf0689c847109bb/httpx/_types.py
RequestContent = Union[str, bytes, Iterable[bytes], AsyncIterable[bytes]]
ResponseContent = Union[str, bytes, Iterable[bytes], AsyncIterable[bytes]]
RequestData = dict
HeaderTypes = Union[
    "Headers",
    Dict[str, str],
    Dict[bytes, bytes],
    Sequence[Tuple[str, str]],
    Sequence[Tuple[bytes, bytes]],
]

JWT = str


@dataclasses.dataclass
class User:
    id: Snowflake
    username: str
    email: EmailStr
    is_active: bool
    is_superuser: bool
    is_verified: bool


@dataclasses.dataclass
class LoginResponse:
    access_token: JWT
    token_type: str

    # def __str__(self):
    #     return


class BaseClient:
    _client_type: ClientType
    _BASE_URL = "http://localhost:8000"

    def __init__(self):
        self._client = self._client_type()

    @property
    def is_closed(self) -> bool:
        return self._client.is_closed

    def close(self) -> None:
        self._client.close()

    def __enter__(self: U) -> U:
        self._client.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # httpx clients have different implementations for close & exit,
        # so we don't just call self.close()
        self._client.__exit__(exc_type, exc_val, exc_tb)


class Client(BaseClient):
    _client_type = httpx.Client

    def _request(
        self,
        method: str,
        url: HttpUrl,
        *,
        return_type: Type[T],
        content: RequestContent = None,
        data: RequestData = None,
        headers: HeaderTypes = None,
        **kwargs,
    ) -> T:
        response = self._client.request(
            method=method,
            url=self._BASE_URL + url,
            content=content,
            data=data,
            headers=headers ** kwargs,
        )
        response.raise_for_status()
        return return_type(**response.json())

    def register(
        self,
        username: str,
        email: EmailStr,
        password: SecretStr,
        grant_type: str = not_set,
        scope: str = not_set,
        client_secret: SecretStr = not_set,
    ) -> User:
        body = create_body(
            ("username", username),
            ("email", email),
            ("password", password),
            ("grant_type", grant_type),
            ("scope", scope),
            ("client_secret", client_secret),
        )
        return self._request(
            "post",
            "/auth/register",
            return_type=User,
            json=body,
        )

    # grant_type: str = None, scope: str = None, client_id: str = None, client_secret: SecretStr = None
    def login(
        self,
        username: str,
        password: SecretStr,
    ) -> LoginResponse:
        return self._request(
            "post",
            "/auth/jwt/login",
            return_type=LoginResponse,
            data=({"username": username, "password": password}),
        )

    def verify(self, token: JWT) -> User:
        return self._request(
            "post", "/auth/verify", return_type=User, json=({"token": token})
        )

    def get_me(self, token: JWT):
        auth_headers = jwt_to_auth_headers(token)
        return self._request("get", "/users/me", return_type=User, headers=auth_headers)

    def update_me(
        self,
        token: JWT,
        email: EmailStr = not_set,
        password: SecretStr = not_set,
        username: str = not_set,
    ):
        auth_headers = jwt_to_auth_headers(token)
        body = create_body(
            ("email", email), ("password", password), ("username", username)
        )
        return self._request(
            "patch", "/users/me", return_type=User, headers=auth_headers, json=body
        )


class AsyncClient(BaseClient):
    _client_type: httpx.AsyncClient

    async def _request(
        self,
        method: str,
        url: HttpUrl,
        *,
        return_type: Type[T],
        content: RequestContent = None,
        data: RequestData = None,
        **kwargs,
    ):
        response = await self._client.request(
            method=method,
            url=self._BASE_URL + url,
            content=content,
            data=data,
            **kwargs,
        )
        response.raise_for_status()
        return return_type(**response.json())

    async def register(
        self,
        username: str,
        email: EmailStr,
        password: SecretStr,
        grant_type: str = not_set,
        scope: str = not_set,
        client_secret: SecretStr = not_set,
    ) -> Coroutine:
        body = create_body(
            ("username", username),
            ("email", email),
            ("password", password),
            ("grant_type", grant_type),
            ("scope", scope),
            ("client_secret", client_secret),
        )
        return await self._request(
            "post",
            "/auth/register",
            return_type=User,
            json=body,
        )

    async def login(
        self,
        username: str,
        password: SecretStr,
    ) -> Coroutine:
        return await self._request(
            "post",
            "/auth/jwt/login",
            return_type=LoginResponse,
            data=({"username": username, "password": password}),
        )

    async def verify(self, token: JWT) -> Coroutine:
        return await self._request(
            "post", "/auth/verify", return_type=User, json=({"token": token})
        )

    async def get_me(self, token: JWT) -> Coroutine:
        auth_headers = jwt_to_auth_headers(token)
        return await self._request(
            "get", "/users/me", return_type=User, headers=auth_headers
        )

    async def update_me(
        self,
        token: JWT,
        email: EmailStr = not_set,
        password: SecretStr = not_set,
        username: str = not_set,
    ) -> Coroutine:
        auth_headers = jwt_to_auth_headers(token)
        body = create_body(
            ("email", email), ("password", password), ("username", username)
        )
        return await self._request(
            "patch", "/users/me", return_type=User, headers=auth_headers, json=body
        )


async def register(
    username: str,
    email: EmailStr,
    password: SecretStr,
    grant_type: str = not_set,
    scope: str = not_set,
    client_secret: SecretStr = not_set,
) -> Coroutine:
    async with AsyncClient() as c:
        return await c.register(
            username,
            email,
            password,
            grant_type=grant_type,
            scope=scope,
            client_secret=client_secret,
        )


async def login(username: str, password: SecretStr):
    async with AsyncClient() as c:
        return await c.login(username, password)


async def verify(token: JWT):
    async with AsyncClient() as c:
        return await c.verify(token)


async def get_me(token: JWT):
    async with AsyncClient() as c:
        return await c.get_me(token)


async def update_me(
    token: JWT,
    email: EmailStr = not_set,
    password: SecretStr = not_set,
    username: str = not_set,
) -> Coroutine:
    async with AsyncClient() as c:
        return await c.update_me(
            token, email=email, password=password, username=username
        )
