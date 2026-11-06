from typing import Annotated

import httpx
import psycopg
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import AuthUser, compute_is_minor, get_current_user
from app.config import settings
from app.db import get_conn
from app.schemas import (
    GraphOut,
    GuardianConsentIn,
    KnowledgeEdgeOut,
    KnowledgeNodeOut,
    OpenRouterKeyIn,
    OpenRouterKeyOut,
    UserOut,
    UserPatch,
)
from app.services.openrouter_key import (
    encrypt_api_key,
    validate_openrouter_key,
)

router = APIRouter(prefix="/api/v1")

_USER_COLS = (
    "id, email, locale, display_name, country_code, birth_year, is_minor, "
    "guardian_consent_at, created_at, updated_at, "
    "(custom_openrouter_api_key_encrypted IS NOT NULL) AS has_openrouter_key"
)


def _user_out(row: dict) -> UserOut:
    return UserOut(
        id=row["id"],
        email=row["email"],
        locale=row["locale"],
        display_name=row.get("display_name"),
        country_code=row.get("country_code"),
        birth_year=row["birth_year"],
        is_minor=row["is_minor"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        guardian_consent_at=row.get("guardian_consent_at"),
        has_openrouter_key=bool(row.get("has_openrouter_key")),
    )


def require_consent_if_minor(conn: psycopg.Connection, user_id) -> None:
    row = conn.execute(
        "SELECT is_minor, guardian_consent_at FROM users WHERE id = %s",
        (user_id,),
    ).fetchone()
    if row and row["is_minor"] and row["guardian_consent_at"] is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guardian consent required",
        )


@router.get("/me", response_model=UserOut)
def get_me(
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> UserOut:
    row = conn.execute(
        f"SELECT {_USER_COLS} FROM users WHERE id = %s",
        (user.id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return _user_out(row)


@router.patch("/me", response_model=UserOut)
def patch_me(
    body: UserPatch,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> UserOut:
    if (
        body.birth_year is None
        and body.locale is None
        and body.display_name is None
        and body.country_code is None
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to update")

    row = conn.execute(
        f"SELECT {_USER_COLS} FROM users WHERE id = %s",
        (user.id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    birth_year = body.birth_year if body.birth_year is not None else row["birth_year"]
    locale = body.locale if body.locale is not None else row["locale"]
    display_name = (
        body.display_name.strip() if body.display_name is not None else row["display_name"]
    )
    country_code = body.country_code if body.country_code is not None else row["country_code"]
    is_minor = compute_is_minor(birth_year)

    updated = conn.execute(
        f"""
        UPDATE users
        SET birth_year = %s,
            locale = %s,
            display_name = %s,
            country_code = %s,
            is_minor = %s,
            updated_at = NOW()
        WHERE id = %s
        RETURNING {_USER_COLS}
        """,
        (birth_year, locale, display_name, country_code, is_minor, user.id),
    ).fetchone()
    conn.commit()
    assert updated is not None
    return _user_out(updated)


@router.post("/me/guardian-consent", response_model=UserOut)
def guardian_consent(
    body: GuardianConsentIn,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> UserOut:
    if not body.confirmed:
        raise HTTPException(status_code=400, detail="Confirmation required")
    updated = conn.execute(
        f"""
        UPDATE users
        SET guardian_consent_at = NOW(), updated_at = NOW()
        WHERE id = %s
        RETURNING {_USER_COLS}
        """,
        (user.id,),
    ).fetchone()
    conn.commit()
    if updated is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _user_out(updated)


@router.put("/me/openrouter-key", response_model=OpenRouterKeyOut)
def put_openrouter_key(
    body: OpenRouterKeyIn,
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> OpenRouterKeyOut:
    profile = conn.execute(
        "SELECT is_minor, guardian_consent_at FROM users WHERE id = %s",
        (user.id,),
    ).fetchone()
    if profile and profile["is_minor"]:
        raise HTTPException(status_code=403, detail="BYO keys disabled for minors")
    if not settings.byo_encryption_key:
        raise HTTPException(status_code=503, detail="BYO_ENCRYPTION_KEY not configured")
    if not validate_openrouter_key(body.api_key.strip()):
        raise HTTPException(status_code=400, detail="OpenRouter key validation failed")
    blob = encrypt_api_key(body.api_key.strip())
    conn.execute(
        """
        UPDATE users
        SET custom_openrouter_api_key_encrypted = %s, updated_at = NOW()
        WHERE id = %s
        """,
        (blob, user.id),
    )
    conn.commit()
    return OpenRouterKeyOut(has_openrouter_key=True)


@router.delete("/me/openrouter-key", response_model=OpenRouterKeyOut)
def delete_openrouter_key(
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> OpenRouterKeyOut:
    conn.execute(
        """
        UPDATE users
        SET custom_openrouter_api_key_encrypted = NULL, updated_at = NOW()
        WHERE id = %s
        """,
        (user.id,),
    )
    conn.commit()
    return OpenRouterKeyOut(has_openrouter_key=False)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> None:
    conn.execute("DELETE FROM users WHERE id = %s", (user.id,))
    conn.commit()

    if not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SUPABASE_SERVICE_ROLE_KEY not configured",
        )

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{user.id}"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }
    with httpx.Client(timeout=15.0) as client:
        resp = client.delete(url, headers=headers)
    if resp.status_code not in (200, 204):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Auth delete failed: {resp.status_code} {resp.text}",
        )


@router.get("/graph", response_model=GraphOut)
def get_graph(
    user: Annotated[AuthUser, Depends(get_current_user)],
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
) -> GraphOut:
    del user
    nodes = conn.execute(
        """
        SELECT id, slug, title, description, node_type::text, domain::text
        FROM knowledge_nodes
        ORDER BY slug
        """
    ).fetchall()
    edges = conn.execute(
        """
        SELECT parent_id, child_id, edge_type::text, weight::float AS weight
        FROM knowledge_edges
        """
    ).fetchall()
    return GraphOut(
        nodes=[KnowledgeNodeOut(**n) for n in nodes],
        edges=[KnowledgeEdgeOut(**e) for e in edges],
    )
