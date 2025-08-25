from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.response import Response


class RoleBasedExamPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        role_names = [role.name.lower() for role in user.role.all()]
        action = view.action
        api_section = getattr(view, 'api_section', None)

        access_rules = {
            'exam_type': {
                'director': 'full',
                'teacher': 'view',
                'student': 'none',
                'office staff': 'full',
                'others': 'none'
            },
            'exam_paper': {
                'director': 'full',
                'teacher': 'full',
                'student': 'none',
                'office staff': 'view',
                'others': 'none'
            },
            'exam_schedule': {
                'director': 'full',
                'teacher': 'full',
                'student': 'view_own',
                'guardian': 'view',
                'office staff': 'partial',
                'others': 'none'
            },

            'student_marks': {
                'director': 'full',
                'teacher': 'view_own_create',
                'student': 'none',
                'office staff': 'view_own_create',
                'others': 'none'
            }
        }

        if not api_section:
            return False

        for role in role_names:
            role = role.lower()
            access_level = access_rules.get(api_section, {}).get(role, 'none')

            if access_level == 'none':
                continue
            elif access_level == 'view' and request.method in SAFE_METHODS:
                return True
            elif access_level == 'partial' and request.method in ['GET', 'POST', 'PUT']:
                return True
            elif access_level == 'view_own' and request.method == 'GET':
                return True
            elif access_level == 'view_own_create' and request.method in ['GET', 'POST', 'PUT']:
                return True
            elif access_level == 'full':
                return True

        return False



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
    

# --------------------- Expense 
class ExpensePermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        roles = [role.name.lower() for role in user.role.all()]
        return any(r in roles for r in ['director', 'office staff'])# Allow only director and office staff for all methods

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)

    
# RBA for termination and reactivation of the user
class RoleBasedUserManagementPermission(BasePermission):
    """
    Permission class for user deactivation / reactivation
    """
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        role_names = [role.name.lower().replace("_", " ").strip() for role in user.role.all()]

        allowed_roles = ['director', 'admin', 'office staff']

        for role in role_names:
            if role in allowed_roles:
                return True

        return False