"""Role permission classes. The global default is IsAuthenticated (default deny);
views then narrow it with one of these."""
from rest_framework.permissions import BasePermission

from accounts.models import Role


class _HasRole(BasePermission):
    roles: tuple[str, ...] = ()

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.role in self.roles)


class IsRecruiter(_HasRole):
    roles = (Role.RECRUITER,)


class IsClient(_HasRole):
    roles = (Role.CLIENT,)


class IsDeliveryHead(_HasRole):
    roles = (Role.DELIVERY_HEAD,)


class IsStaffRole(_HasRole):
    """Recruiter or delivery head: internal users, never clients."""

    roles = (Role.RECRUITER, Role.DELIVERY_HEAD)
