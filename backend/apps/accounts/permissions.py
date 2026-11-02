from rest_framework.permissions import BasePermission

from .models import User


class HasRole(BasePermission):
    """Базовый класс: пускает только пользователей с одной из allowed_roles."""

    allowed_roles: tuple = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in self.allowed_roles)


class IsParticipant(HasRole):
    allowed_roles = (User.Role.PARTICIPANT, User.Role.ADMIN)


class IsJury(HasRole):
    allowed_roles = (User.Role.JURY, User.Role.ADMIN)


class IsOrganizer(HasRole):
    allowed_roles = (User.Role.ORGANIZER, User.Role.ADMIN)


class IsAdminRole(HasRole):
    allowed_roles = (User.Role.ADMIN,)


class IsEmailVerified(BasePermission):
    message = "Сначала подтверди email."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_email_verified)