# from rest_framework.permissions import BasePermission, SAFE_METHODS

# class RoleBasedPermission(BasePermission):
#     def has_permission(self, request, view):
#         user = request.user
#         role = user.role.name if user.role else None

        
#         if role == 'director':
#             return True  
#         elif role == 'office staff':
#             return True  
#         elif role == 'teacher':
#             if request.method == 'GET':
#                 return True  
#             return False
#         return False

from rest_framework.permissions import BasePermission, SAFE_METHODS

class RoleBasedPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        # Get all role names for the user (ManyToMany)
        role_names = [role.name.lower() for role in user.role.all()]

        if 'director' in role_names:
            return True

        elif 'office staff' in role_names:
            return True

        elif 'teacher' in role_names:
            return request.method in SAFE_METHODS  # GET/HEAD/OPTIONS only

        return False
