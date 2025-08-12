from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.response import Response

class RoleBasedPermission(BasePermission):
    """
    For report card and related views, allow access based on user roles.
    """

    def has_permission(self, request, view):
        print("Checking permissions for user:", request.user)

        user_roles = request.user.role.all().values_list('name', flat=True)

        # Allow all GETs for Director and Office Staff
        if request.method in SAFE_METHODS:
            if "director" in user_roles or "office_staff" in user_roles:
                return True
            elif "teacher" in user_roles:
                return True
            elif "student" in user_roles or "guardian" in user_roles:
                return True
            return False

        # Allow POST and PATCH for Director and assigned Teacher
        elif request.method in ['POST', 'PATCH', 'DELETE']:
            if "director" in user_roles:
                return True
            elif "teacher" in user_roles:
                return True
            return False

        # Deny everything else by default
        return False



class IsDirector(BasePermission):
    """
    Allows access only to users with the 'Director' role.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.filter(name="Director").exists()