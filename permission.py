

# from rest_framework.permissions import BasePermission, SAFE_METHODS

# class RoleBasedPermission(BasePermission):
#     def has_permission(self, request, view):
#         user = request.user

#         # Get all role names for the user (ManyToMany)
#         role_names = [role.name.lower() for role in user.role.all()]

#         if 'director' in role_names:
#             return True

#         elif 'office staff' in role_names:
#             return True

#         elif 'teacher' in role_names:
#             return request.method in SAFE_METHODS  # GET/HEAD/OPTIONS only

#         return False


from rest_framework.permissions import BasePermission, SAFE_METHODS
from teacher.models import Teacher, TeacherYearLevel

class RoleBasedPermission(BasePermission):
    """
    Director / Office Staff → full CRUD + full queryset
    Teacher → sirf GET/HEAD/OPTIONS + apna hi data
    Baaki sab → deny
    """

    def has_permission(self, request, view):
        user = request.user
        role_names = [role.name.lower() for role in user.role.all()]

        # Director & Office Staff: all methods allowed
        if 'director' in role_names or 'office staff' in role_names:
            return True

        # Teacher: only safe methods
        if 'teacher' in role_names:
            return request.method in SAFE_METHODS

        # Other roles: deny
        return False

    def filter_queryset(self, request, queryset, view):
        """
        Role-based queryset filtering
        """
        user = request.user
        role_names = [role.name.lower() for role in user.role.all()]

        if 'director' in role_names or 'office staff' in role_names:
            return queryset

        elif 'teacher' in role_names:
            try:
                teacher = Teacher.objects.get(user=user)
                return queryset.filter(teacher=teacher)
            except Teacher.DoesNotExist:
                return queryset.none()

        return queryset.none()
