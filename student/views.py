from argparse import Action
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response


from director.models import Address, Role, YearLevel

from .models import GuardianType, Student, StudentYearLevel
from .serializers import GuardianTypeSerializer, StudentSerializer, StudentYearLevelSerializer
from rest_framework import status
from rest_framework import filters
from rest_framework.response import Response
from .serializers import GuardianSerializer
from .models import Guardian
from director.models import Role
from rest_framework.filters import SearchFilter
from rest_framework import viewsets
from .pagination import CreatePagination
from datetime import date  
from rest_framework.decorators import action 
from rest_framework.permissions import IsAuthenticated,AllowAny


@api_view(["GET", "POST", "PUT", "DELETE"])
def GuardianTypeView(request, pk=None):
    if request.method == "GET":
        if pk is not None:
            try:
                guardian_type = GuardianType.objects.get(id=pk)
                serializer = GuardianTypeSerializer(guardian_type, many=False)
                return Response(serializer.data, status.HTTP_200_OK)

            except GuardianType.DoesNotExist:
                return Response(
                    {"message": "Data Not Found"}, status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {"message": "Something went wrong"},
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        else:
            guardian_types = GuardianType.objects.all()
            serializer = GuardianTypeSerializer(guardian_types, many=True)
            return Response(serializer.data, status.HTTP_200_OK)

    elif request.method == "POST":
        json_data = request.data

        if json_data.get("name", None) is None:
            return Response({"message": "Invalid Data"}, status.HTTP_400_BAD_REQUEST)

        json_data["name"] = json_data["name"].lower()
        serializer = GuardianTypeSerializer(data=json_data)

        if serializer.is_valid():

            if GuardianType.objects.filter(name=json_data["name"]).exists():
                return Response(
                    {"message": "Guardian type Already Exists"},
                    status.HTTP_400_BAD_REQUEST,
                )

            serializer.save()
            return Response(
                {"message": "GuardianType Added Successfully"}, status.HTTP_201_CREATED
            )
        return Response({"message": "Invalid Data"}, status.HTTP_400_BAD_REQUEST)

    elif request.method == "PUT":

        if request.data.get("name", None) is None:
            return Response({"message": "Invalid Data"}, status.HTTP_400_BAD_REQUEST)

        request.data["name"] = request.data["name"].lower()

        try:
            guardian_type = GuardianType.objects.get(id=pk)
            serializer = GuardianTypeSerializer(
                instance=guardian_type, data=request.data, partial=True
            )

            if serializer.is_valid():

                if GuardianType.objects.filter(name=request.data["name"]).exists():
                    return Response(
                        {"message": "Guardian type Already Exists"},
                        status.HTTP_400_BAD_REQUEST,
                    )

                serializer.save()
                return Response(
                    {"message": "GuardianType updated Successfully"},
                    status.HTTP_200_OK,
                )

            return Response({"message": "Invalid Data"}, status.HTTP_400_BAD_REQUEST)

        except GuardianType.DoesNotExist:
            return Response({"message": "Data Not Found"}, status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {"message": "something went wrong"},
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    elif request.method == "DELETE":

        if pk is None:
            return Response(
                {"message": "Id is Required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            get = GuardianType.objects.get(id=pk)
            get.delete()
            return Response(
                {"message": "GuardianType Delete Successfully"}, status.HTTP_200_OK
            )
        except GuardianType.DoesNotExist:
            return Response({"message": "Data Not Found"}, status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"message": "Something went wrong"},
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# 
    
    
class StudentView(ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__email', 'user__first_name', 'enrolment_date']
    
    def get_permissions(self):
        """Public access for list/retrieve; JWT required for others."""
        if self.action in ['list', 'retrieve','create','update', 'partial_update']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user_instance = instance.user
        student_role = Role.objects.get(name='student')

        
        user_instance.role.remove(student_role)
        other_roles = user_instance.role.exclude(name='student')
        if other_roles.exists():
                self.perform_destroy(instance)
                return Response({"success": "Student profile deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        else:
                
                instance.delete()
                self.perform_destroy(user_instance)
                return Response({"success": "Student profile and related user deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
       


    def calculate_age(self, birth_date):
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    @action(detail=False, methods=['get'], url_path='by-year-level-id/(?P<year_level_id>[^/.]+)')
    def by_year_level_id(self, request, year_level_id=None):    
        student_year_levels = StudentYearLevel.objects.filter(level_id=year_level_id)
        
        if not student_year_levels.exists():
            return Response({"message": "No students found for the specified year level"}, status=status.HTTP_404_NOT_FOUND)

        students_data = []

        for sy in student_year_levels:
            student = sy.student
            user = student.user
            address_obj = Address.objects.filter(user=user).first()

            full_address = (
                f"{address_obj.house_no}, {address_obj.address_line}, {address_obj.city.name}, "
                f"{address_obj.state.name}, {address_obj.country.name}, Area Code: {address_obj.area_code}"
                if address_obj else "N/A"
            )

            students_data.append({
                "student_name": f"{user.first_name} {user.last_name}",
                "age": self.calculate_age(student.date_of_birth) if student.date_of_birth else "N/A",
                "gender": student.gender,
                "mobile_number": getattr(user, 'phone', "N/A"),
                "address": full_address,
                "year_level": sy.level.level_name,
                "school_year": sy.year.year_name
            })

        return Response(students_data, status=status.HTTP_200_OK)
    
    # *************************JWTlogin student**************************
    
    @action(detail=False, methods=['get', 'put', 'patch'], url_path='student_my_profile', permission_classes=[IsAuthenticated])
    def student_my_profile(self, request):
        user = request.user

        try:
            student = Student.objects.get(user=user)
        except Student.DoesNotExist:
            return Response({"error": "No student profile found for this user."}, status=status.HTTP_404_NOT_FOUND)

        if request.method in ['PUT', 'PATCH']:
            partial = request.method == 'PATCH'
            serializer = self.get_serializer(student, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"success": "Student profile updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)

        serializer = self.get_serializer(student)
        return Response(serializer.data, status=status.HTTP_200_OK)










class GuardianProfileView(viewsets.ModelViewSet):
    queryset = Guardian.objects.all()
    serializer_class = GuardianSerializer
    filter_backends = [SearchFilter]
    search_fields = ['user__email','user__first_name','user__guardian_relation__phone_no']
    pagination_class = CreatePagination
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve','create','update', 'partial_update']:
            return [AllowAny()]  # Public access
        return [IsAuthenticated()]  # JWT required for update, my-profile, delete

  
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user_instance = instance.user
        
        try:
            role = Role.objects.get(name='guardian')
        except Role.DoesNotExist:
            return Response({"error": "Guardian role does not exist"}, status=status.HTTP_404_NOT_FOUND)

        if user_instance.role.exclude(name='guardian').exists():
            user_instance.role.remove(role)
            instance.delete()

            return Response({"message": "Role removed successfully from user and deletd data from gaurdian"}, status=status.HTTP_200_OK)
        else:
            try:
                self.perform_destroy(instance)
                user_instance.delete()
                return Response({"message": "Successfully deleted"}, status=status.HTTP_204_NO_CONTENT)
            except Exception as e:
                return Response ({"error": "Deletion unsuccessful: Error deleting user"})
            
            
    # **********************Jwt***************    
    @action(detail=False, methods=['get', 'put', 'patch'], url_path='guardian_my_profile', permission_classes=[IsAuthenticated])
    def guardian_my_profile(self, request):
        user = request.user

        try:
            guardian = Guardian.objects.get(user=user)
        except Guardian.DoesNotExist:
            return Response({"error": "Guardian profile not found for this user."}, status=status.HTTP_404_NOT_FOUND)

        if request.method in ['PUT', 'PATCH']:
            partial = request.method == 'PATCH'
            serializer = self.get_serializer(guardian, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"success": "Guardian profile updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)

        serializer = self.get_serializer(guardian)
        return Response(serializer.data, status=status.HTTP_200_OK)    
            
            


# As of 19June25 at 12:46 PM
from django_filters.rest_framework import DjangoFilterBackend

class StudentYearLevelView(viewsets.ModelViewSet):
    queryset = StudentYearLevel.objects.all()
    serializer_class = StudentYearLevelSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['level__id']  #  GET /student-year-levels/?level__id=2
    search_fields = ['level__level_name']  #  GET /student-year-levels/?search=Nursery
    
    # combine search endpoint GET /student-year-levels/?level__id=2&search=Nursery

            
