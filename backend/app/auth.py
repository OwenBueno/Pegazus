from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import settings

bearer = HTTPBearer(auto_error=False)


@dataclass
class AuthUser:
    id: UUID
    email: str | None


def compute_is_minor(birth_year: int | None) -> bool:
    if birth_year is None:
        return False
    age = date.today().year - birth_year
    return age < settings.minor_age_threshold


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    # Supabase local (CLI ≥ 2.x) signs access tokens with ES256; verify via JWKS.
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(url, cache_keys=True)


def _decode_access_token(token: str) -> dict:
    header = jwt.get_unverified_header(token)
    alg = header.get("alg", "HS256")
    try:
        if alg == "ES256":
            key = _jwks_client().get_signing_key_from_jwt(token).key
            return jwt.decode(
                token,
                key,
                algorithms=["ES256"],
                audience="authenticated",
            )
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> AuthUser:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    payload = _decode_access_token(creds.credentials)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid subject")
    return AuthUser(id=UUID(sub), email=payload.get("email"))
