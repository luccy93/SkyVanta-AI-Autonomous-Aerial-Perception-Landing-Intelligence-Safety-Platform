"""Security policies, authorization scopes, and hierarchical permission rules."""

from enum import Enum
from typing import Set


class Scope(str, Enum):
    """Canonical authorization scopes for API access."""
    READ = "read"
    EXECUTE = "execute"
    ADMIN = "admin"


# Scope hierarchy: higher privileges imply lower ones
_SCOPE_HIERARCHY = {
    Scope.ADMIN: {Scope.ADMIN, Scope.EXECUTE, Scope.READ},
    Scope.EXECUTE: {Scope.EXECUTE, Scope.READ},
    Scope.READ: {Scope.READ},
}


def has_scope(granted_scopes: Set[Scope], required_scope: Scope) -> bool:
    """Evaluates whether the granted scopes satisfy the required permission scope.

    Args:
        granted_scopes: Set of Scope enums associated with the authenticated identity.
        required_scope: The minimum Scope required to access the resource.

    Returns:
        True if permissions are sufficient; False otherwise.
    """
    for scope in granted_scopes:
        implied = _SCOPE_HIERARCHY.get(scope, set())
        if required_scope in implied:
            return True
    return False
