from rest_framework.permissions import BasePermission

class IsDirector(BasePermission):
    """
    Allows access only to users with the 'Director' role.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.filter(name="Director").exists()
