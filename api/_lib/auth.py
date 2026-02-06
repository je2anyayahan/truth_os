from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from fastapi import Header, HTTPException, status


Role = Literal["operator", "basic"]


@dataclass(frozen=True)
class User:
    user_id: str
    role: Role


def get_user(
    x_user_role: Optional[str] = Header(default=None),
    x_user_id: Optional[str] = Header(default=None),
) -> User:
    """
    Simplified auth:
    - Provide headers:
      - x-user-role: operator|basic
      - x-user-id: any string (optional; defaults to 'demo-user')
    """
    role = (x_user_role or "operator").strip().lower()
    if role not in ("operator", "basic"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid x-user-role (use operator|basic)",
        )
    return User(user_id=(x_user_id or "demo-user"), role=role)  # type: ignore[return-value]


def require_operator(user: User) -> None:
    if user.role != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="operator role required",
        )

