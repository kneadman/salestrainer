from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    INTERNAL_ADMIN = "internal_admin"
    CLIENT_LEAD = "client_lead"
    CLIENT_MANAGER = "client_manager"
    CLIENT_USER_LEGACY = "client_user"


CLIENT_ROLES = frozenset({UserRole.CLIENT_LEAD, UserRole.CLIENT_MANAGER})
ACTIVE_CLIENT_ROLES = frozenset({UserRole.CLIENT_LEAD, UserRole.CLIENT_MANAGER})


def normalize_role(role: str | UserRole) -> UserRole:
    value = role.value if isinstance(role, UserRole) else role
    if value == UserRole.CLIENT_USER_LEGACY.value:
        return UserRole.CLIENT_MANAGER
    return UserRole(value)


def role_value(role: str | UserRole) -> str:
    return normalize_role(role).value


def is_internal_admin(role: str | UserRole) -> bool:
    return normalize_role(role) == UserRole.INTERNAL_ADMIN


def is_client_role(role: str | UserRole) -> bool:
    return normalize_role(role) in CLIENT_ROLES
