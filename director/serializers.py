from datetime import *
import re
from rest_framework import serializers
from .models import *
from django.core.exceptions import MultipleObjectsReturned
from django.db import IntegrityError
from student.serializers import *
# from authentication.serializers import UserSerializer
from uuid import uuid4
from django.utils import timezone
from decimal import Decimal
from collections import defaultdict
from django.db.models import Max


from django.utils import timezone
from decimal import Decimal
from collections import defaultdict
from django.db.models import Max
from decimal import Decimal
from django.db.models import Sum
import calendar
from django.core.exceptions import ValidationError
import os
from dateutil.relativedelta import relativedelta
from django.conf import settings

class YearLevelSerializer(serializers.ModelSerializer):   # coomented as of 05June25 at 01:36 AM
    class Meta:
        model = YearLevel
        fields = "__all__"

class SchoolYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolYear
        fields = "__all__"


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class ClassRoomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassRoomType
        fields = "__all__"
        
 


class ClassRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassRoom
        fields = ['id', 'room_type', 'room_name', 'capacity']
        read_only_fields = ['id']



class BankingDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankingDetail
        fields = ["id", "account_no", "ifsc_code", "holder_name"]
        extra_kwargs = {
            "user": {"read_only": True}
        }

    
    def create(self, validated_data):
        user = self.context.get("user")
        if not user:
            raise serializers.ValidationError("User is required to create banking detail.")
        return BankingDetail.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        account_no = validated_data.get("account_no")
        if account_no and account_no != instance.account_no:
            if BankingDetail.objects.filter(account_no=account_no).exclude(id=instance.id).exists():
                raise serializers.ValidationError({
                    "account_no": "This account number is already in use by another user."
                })
        instance.account_no = validated_data.get("account_no", instance.account_no)
        instance.ifsc_code = validated_data.get("ifsc_code", instance.ifsc_code)
        instance.holder_name = validated_data.get("holder_name", instance.holder_name)
        instance.save()
        return instance


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name"]

    def create_or_get_role(self, role_name):
        existing_role = Role.objects.filter(name=role_name).first()
        if existing_role:
            return existing_role
        else:
            new_role = Role.objects.create(name=role_name)
            return new_role


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = "__all__"
        
        


class subjectSerializer(serializers.ModelSerializer):
    department_name = serializers.SerializerMethodField()  # repalced department to department_name because of SerializerMethodField (Read Only Field).

    class Meta:
        model = Subject
        fields = ['id', 'subject_name', 'department', 'department_name','year_levels'] 

    def get_department_name(self, obj):
        return obj.department.department_name if obj.department else None



class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = "__all__"


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = "__all__"




class AddressSerializer(serializers.ModelSerializer):
    country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all(),write_only=True)
    state = serializers.PrimaryKeyRelatedField(queryset=State.objects.all(),write_only=True)
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(),write_only=True)

    country_name = serializers.CharField(source='country.name', read_only=True)
    state_name = serializers.CharField(source='state.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)

    class Meta:
        model = Address
        fields = [
            'id', 'user', 'house_no', 'habitation', 'ward_no', 'zone_no', 'block', 'district', 'division', 'area_code',
            'country', 'state', 'city', 'address_line',
            'country_name', 'state_name', 'city_name'
        ]
        extra_kwargs = {
            'user': {'read_only': True}
        }

    def validate(self, data):
        # user = data.get('user')  # No need to get user here, it's read-only
        house_no = data.get('house_no')
        area_code = data.get('area_code')
        country = data.get('country')
        state = data.get('state')
        city = data.get('city')
        address_line = data.get('address_line')

        # Access the user from the serializer context
        user = self.context.get('user')

        if Address.objects.filter(
            user=user,
            house_no=house_no,
            area_code=area_code,
            country=country,
            state=state,
            city=city,
            address_line=address_line
        ).exists():
            raise serializers.ValidationError("Address already exists for the user.")

        return data

    def create(self, validated_data):
            user = self.context['request'].user  # assuming request is passed in context
            return Address.objects.create(user=user, **validated_data)



class SchoolYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolYear
        fields = "__all__"


class PeriodSerializer(serializers.ModelSerializer):
    year = serializers.PrimaryKeyRelatedField(queryset=SchoolYear.objects.all())

    class Meta:
        model = Period
        fields = ["id","year", "name", "start_period_time", "end_period_time"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        try:
            representation["year"] = instance.year.year_name
        except AttributeError:
            representation["year"] = None
        return representation


class TermSerializer(serializers.ModelSerializer):
    year = serializers.PrimaryKeyRelatedField(queryset=SchoolYear.objects.all())

    class Meta:
        model = Term
        fields = ["id", "year", "term_number", "start_date", "end_date"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["year"] = instance.year.year_name
        return representation


class DirectorProfileSerializer(serializers.ModelSerializer):
    # User fields
    first_name = serializers.CharField(max_length=100, write_only=True)
    middle_name = serializers.CharField(max_length=100, write_only=True, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=100, write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_null=True)
    user_profile = serializers.ImageField(required=False, allow_null=True, write_only=True)

    # Director fields
    phone_no = serializers.CharField(required=False,allow_blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?\d{10,15}$',
                message="Enter a valid contact number (10-15 digits, optional + at start).")])
    gender = serializers.ChoiceField(
        choices=[('Male','Male'),('Female','Female'),('Other','Other')],
        required=False,
        error_messages={"invalid_choice": "Gender must be Male, Female, or Other."}
    )

    class Meta:
        model = Director
        exclude = ["user"]

    def create(self, validated_data):
        # Extract user-related data
        user_data = {
            "first_name": validated_data.pop("first_name"),
            "middle_name": validated_data.pop("middle_name", ""),
            "last_name": validated_data.pop("last_name"),
            "email": validated_data.pop("email"),
            "password": validated_data.pop("password", ""),
            "user_profile": validated_data.pop("user_profile", None),
        }

        phone_no = validated_data.pop("phone_no", None)
        gender = validated_data.pop("gender", None)

        # Assign role
        try:
            role, _ = Role.objects.get_or_create(name="director")
        except MultipleObjectsReturned:
            raise serializers.ValidationError("Multiple 'director' roles exist. Please fix your roles table.")

        # Get or create user
        user = User.objects.filter(email=user_data["email"]).first()
        if user:
            if not user.role.filter(name="director").exists():
                user.role.add(role)
        else:
            user = User.objects.create_user(**user_data)
            user.role.add(role)
            user.save()

        try:
            director_profile = Director.objects.create(
                user=user,
                phone_no=phone_no,
                gender=gender,
                **validated_data
            )
        except IntegrityError:
            raise serializers.ValidationError("User with this email already exists.")

        return director_profile

    def update(self, instance, validated_data):
        user = instance.user

        # Update user info
        user.first_name = validated_data.get("first_name", user.first_name)
        user.middle_name = validated_data.get("middle_name", user.middle_name)
        user.last_name = validated_data.get("last_name", user.last_name)
        user.email = validated_data.get("email", user.email)

        if "password" in validated_data and validated_data["password"]:
            user.set_password(validated_data["password"])

        if "user_profile" in validated_data:
            user.user_profile = validated_data.get("user_profile")

        # Update director fields
        instance.phone_no = validated_data.get("phone_no", instance.phone_no)
        instance.gender = validated_data.get("gender", instance.gender)

        try:
            user.save()
            instance.save()
        except IntegrityError:
            raise serializers.ValidationError("Failed to update. Email may already exist.")

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.update({
            "first_name": instance.user.first_name,
            "middle_name": instance.user.middle_name,
            "last_name": instance.user.last_name,
            "email": instance.user.email,
            "user_profile": instance.user.user_profile.url if instance.user.user_profile else None,
            "phone_no": instance.phone_no,
            "gender": instance.gender,
        })
        return representation



class AdmissionSerializer(serializers.ModelSerializer):
    # enrollment_no = serializers.ReadOnlyField()
    # Use SerializerMethodField to output nested student and guardian data
    student_input = serializers.SerializerMethodField(read_only=True)
    guardian_input = serializers.SerializerMethodField(read_only=True)
    
    address = serializers.SerializerMethodField(read_only=True)
    banking_detail = serializers.SerializerMethodField(read_only=True)

    guardian_type = serializers.SerializerMethodField(read_only=True)
    guardian_type_input = serializers.SlugRelatedField(
        slug_field='name',
        queryset=GuardianType.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    
    year_level = serializers.SlugRelatedField(
        slug_field='level_name',
        queryset=YearLevel.objects.all(),
        required=False,
        allow_null=True,
    )
    
    school_year = serializers.SlugRelatedField(
        slug_field='year_name',
        queryset=SchoolYear.objects.all(),
        required=False,
        allow_null=True,
    )

    # These are write-only inputs for creating/updating admission
    student = StudentSerializer(write_only=True, required=True)
    guardian = GuardianSerializer(write_only=True, required=True)
    address_input = AddressSerializer(write_only=True, required=False, allow_null=True)
    banking_detail_input = BankingDetailsSerializer(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Admission
        fields = [
            'id',
            'student_input', 'guardian_input',  # output nested data
            'address', 'banking_detail',
            'student', 'guardian',  # write-only input nested data
            'address_input', 'banking_detail_input',
            'guardian_type', 'guardian_type_input',
            'year_level', 'school_year',
            'admission_date', 'previous_school_name', 'previous_standard_studied',
            'tc_letter', 'emergency_contact_no', 'entire_road_distance_from_home_to_school',
            'obtain_marks', 'total_marks', 'previous_percentage','enrollment_no','is_rte', 'rte_number'
        ]
        read_only_fields = [
            'admission_date',
            'student_input',
            'guardian_input',
            'guardian_type',
            'address',
            'banking_detail',
            'enrollment_no'
        ]

    def get_student_input(self, obj):
        if obj.student:
            return StudentSerializer(obj.student).data
        return None

    def get_guardian_input(self, obj):
        if obj.guardian:
            return GuardianSerializer(obj.guardian).data
        return None

    def get_address(self, obj):
        address = Address.objects.filter(user=obj.student.user).first()
        return AddressSerializer(address).data if address else None

    def get_banking_detail(self, obj):
        banking = BankingDetail.objects.filter(user=obj.student.user).first()
        return BankingDetailsSerializer(banking).data if banking else None

    def get_guardian_type(self, obj):
        try:
            sg = StudentGuardian.objects.get(student=obj.student, guardian=obj.guardian)
            return sg.guardian_type.name
        except StudentGuardian.DoesNotExist:
            return None

    def create(self, validated_data):
        is_rte = validated_data.pop('is_rte', False)
        rte_number = validated_data.pop('rte_number', None)
        student_data = validated_data.pop('student')
        guardian_data = validated_data.pop('guardian')
        address_data = validated_data.pop('address_input', None)
        banking_data = validated_data.pop('banking_detail_input', None)
        guardian_type = validated_data.pop('guardian_type_input', None)
        year_level = validated_data.pop('year_level', None)
        school_year = validated_data.pop('school_year', None)

        # --- Student processing ---
        classes_data = student_data.pop('classes', [])
        if isinstance(classes_data, str):
            try:
                classes_data = [int(classes_data)]
            except ValueError:
                raise serializers.ValidationError({"student.classes": "Invalid class ID format."})

        user_data = {
            'first_name': student_data.pop('first_name', ''),
            'middle_name': student_data.pop('middle_name', ''),
            'last_name': student_data.pop('last_name', ''),
            'email': student_data.pop('email'),
            'password': student_data.pop('password', None),
            'user_profile': student_data.pop('user_profile', None),
        }

        user = User.objects.filter(email__iexact=user_data['email']).first()
        if not user:
            role, _ = Role.objects.get_or_create(name='student')
            user = User.objects.create_user(**user_data)
            user.role.add(role)


        # ===== Generate scholar_number here =====
        last_student = Student.objects.order_by('-id').first()
        
        if last_student and last_student.scholar_number and last_student.scholar_number.isdigit():
            next_number = int(last_student.scholar_number) + 1
        else:
            next_number = 1
        student_data['scholar_number'] = str(next_number).zfill(4)

        student, created = Student.objects.get_or_create(user=user, defaults=student_data)
        if not created:
            raise serializers.ValidationError({"student": "Student already exists for this user."})

        if classes_data:
            student.classes.set(classes_data)

        # --- Address and banking ---
        if address_data:
            Address.objects.update_or_create(user=user, defaults=address_data)
        if banking_data:
            BankingDetail.objects.update_or_create(user=user, defaults=banking_data)

        # --- FIXED: Guardian user creation or auto-fill ---
        guardian_user_data = {
            'first_name': guardian_data.pop('first_name', ''),
            'middle_name': guardian_data.pop('middle_name', ''),
            'last_name': guardian_data.pop('last_name', ''),
            'email': guardian_data.pop('email'),
            'password': guardian_data.pop('password', None),
            'user_profile': guardian_data.pop('user_profile', None),
        }

        guardian_user = User.objects.filter(email__iexact=guardian_user_data['email']).first()
        
        if not guardian_user:
            # New guardian - create with password
            role, _ = Role.objects.get_or_create(name='guardian')
            guardian_user = User.objects.create_user(**guardian_user_data)
            guardian_user.role.add(role)
        else:
            # Existing guardian - update details but DON'T change password
            password = guardian_user_data.pop('password', None)
            
            # Only update non-empty values
            for attr, value in guardian_user_data.items():
                if value:
                    setattr(guardian_user, attr, value)
            
            # Only set password if explicitly provided
            if password:
                guardian_user.set_password(password)
            
            guardian_user.is_active = True
            guardian_user.save()

        # --- Guardian model creation or update ---
        guardian, created = Guardian.objects.get_or_create(user=guardian_user, defaults=guardian_data)
        if not created and guardian_data:
            # Update existing guardian details
            guardian_serializer = GuardianSerializer(guardian, data=guardian_data, partial=True)
            guardian_serializer.is_valid(raise_exception=True)
            guardian_serializer.save()

        # --- Admission creation ---
        admission = Admission.objects.create(
            student=student,
            guardian=guardian,
            previous_school_name=validated_data.get('previous_school_name'),
            previous_standard_studied=validated_data.get('previous_standard_studied'),
            tc_letter=validated_data.get('tc_letter'),
            year_level=year_level,
            school_year=school_year,
            emergency_contact_no=validated_data.get('emergency_contact_no'),
            entire_road_distance_from_home_to_school=validated_data.get('entire_road_distance_from_home_to_school'),
            obtain_marks=validated_data.get('obtain_marks'),
            total_marks=validated_data.get('total_marks'),
            previous_percentage=validated_data.get('previous_percentage'),
            enrollment_no=validated_data.get('enrollment_no'),
            is_rte=is_rte,
            rte_number=rte_number
        )

        if guardian_type:
            StudentGuardian.objects.update_or_create(
                student=student, guardian=guardian, defaults={'guardian_type': guardian_type}
            )

        if year_level and school_year:
            StudentYearLevel.objects.update_or_create(
                student=student, level=year_level, year=school_year
            )

        return admission


    def update(self, instance, validated_data):
        instance.is_rte = validated_data.get('is_rte', instance.is_rte)
        instance.rte_number = validated_data.get('rte_number', instance.rte_number)
        student_data = validated_data.pop('student', None)
        guardian_data = validated_data.pop('guardian', None)
        address_data = validated_data.pop('address_input', None)
        banking_data = validated_data.pop('banking_detail_input', None)
        guardian_type = validated_data.pop('guardian_type_input', None)
        year_level = validated_data.pop('year_level', None)
        school_year = validated_data.pop('school_year', None)

        user = self.context.get("user") or instance.student.user

        if student_data:
            student_serializer = StudentSerializer(instance.student, data=student_data, partial=True)
            student_serializer.is_valid(raise_exception=True)
            student_serializer.save()

            classes_data = student_data.get('classes')
            if isinstance(classes_data, str):
                try:
                    classes_data = [int(classes_data)]
                except ValueError:
                    raise serializers.ValidationError({"student.classes": "Invalid class ID format."})

            if classes_data:
                instance.student.classes.set(classes_data)

        if guardian_data:
            # FIXED: Guardian update with proper password handling
            guardian_user = instance.guardian.user
            guardian_user_data = {
                'first_name': guardian_data.pop('first_name', ''),
                'middle_name': guardian_data.pop('middle_name', ''),
                'last_name': guardian_data.pop('last_name', ''),
                'email': guardian_data.pop('email', ''),
                'password': guardian_data.pop('password', None),
                'user_profile': guardian_data.pop('user_profile', None),
            }
            
            password = guardian_user_data.pop('password', None)
            
            # Only update non-empty values
            for attr, value in guardian_user_data.items():
                if value:
                    setattr(guardian_user, attr, value)
            
            # Only set password if explicitly provided
            if password:
                guardian_user.set_password(password)
            
            guardian_user.save()
            
            # Update guardian model
            guardian_serializer = GuardianSerializer(instance.guardian, data=guardian_data, partial=True)
            guardian_serializer.is_valid(raise_exception=True)
            guardian_serializer.save()

        if address_data:
            for key in ['city', 'state', 'country']:
                val = address_data.get(key)
                if hasattr(val, 'id'):
                    address_data[key] = val.id

            try:
                address_instance = Address.objects.get(user=user)
                address_serializer = AddressSerializer(address_instance, data=address_data, partial=True)
            except Address.DoesNotExist:
                address_serializer = AddressSerializer(data=address_data)

            address_serializer.is_valid(raise_exception=True)
            address_serializer.save(user=user)

        if banking_data:
            current_account_no = str(banking_data.get('account_no'))

            try:
                banking_instance = BankingDetail.objects.get(user=user)
                existing_account_no = str(banking_instance.account_no)

                if existing_account_no == current_account_no:
                    banking_data.pop('account_no', None)
                else:
                    if BankingDetail.objects.filter(account_no=current_account_no).exclude(user_id=user.id).exists():
                        raise serializers.ValidationError({
                            "banking_detail_input": {
                                "account_no": ["This account number is already in use by another user."]
                            }
                        })

                banking_serializer = BankingDetailsSerializer(banking_instance, data=banking_data, partial=True)
                banking_serializer.is_valid(raise_exception=True)
                banking_serializer.save(user=user)

            except BankingDetail.DoesNotExist:
                if BankingDetail.objects.filter(account_no=current_account_no).exists():
                    raise serializers.ValidationError({
                        "banking_detail_input": {
                            "account_no": ["This account number is already in use."]
                        }
                    })

                banking_serializer = BankingDetailsSerializer(data=banking_data)
                banking_serializer.is_valid(raise_exception=True)
                banking_serializer.save(user=user)

        if guardian_type:
            StudentGuardian.objects.update_or_create(
                student=instance.student,
                guardian=instance.guardian,
                defaults={"guardian_type": guardian_type}
            )

        if year_level:
            instance.year_level = year_level
        if school_year:
            instance.school_year = school_year

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance



# # # ***************change variable name *****************************
# class AdmissionSerializer(serializers.ModelSerializer):
#     # enrollment_no = serializers.ReadOnlyField()
#     # Use SerializerMethodField to output nested student and guardian data
#     student_input = serializers.SerializerMethodField(read_only=True)
#     guardian_input = serializers.SerializerMethodField(read_only=True)
    
#     address = serializers.SerializerMethodField(read_only=True)
#     banking_detail = serializers.SerializerMethodField(read_only=True)

#     guardian_type = serializers.SerializerMethodField(read_only=True)
#     guardian_type_input = serializers.SlugRelatedField(
#         slug_field='name',
#         queryset=GuardianType.objects.all(),
#         write_only=True,
#         required=False,
#         allow_null=True,
#     )
    
#     year_level = serializers.SlugRelatedField(
#         slug_field='level_name',
#         queryset=YearLevel.objects.all(),
#         required=False,
#         allow_null=True,
#     )
    
#     school_year = serializers.SlugRelatedField(
#         slug_field='year_name',
#         queryset=SchoolYear.objects.all(),
#         required=False,
#         allow_null=True,
#     )

#     # These are write-only inputs for creating/updating admission
#     student = StudentSerializer(write_only=True, required=True)
#     guardian = GuardianSerializer(write_only=True, required=True)
#     address_input = AddressSerializer(write_only=True, required=False, allow_null=True)
#     banking_detail_input = BankingDetailsSerializer(write_only=True, required=False, allow_null=True)

#     class Meta:
#         model = Admission
#         fields = [
#             'id',
#             'student_input', 'guardian_input',  # output nested data
#             'address', 'banking_detail',
#             'student', 'guardian',  # write-only input nested data
#             'address_input', 'banking_detail_input',
#             'guardian_type', 'guardian_type_input',
#             'year_level', 'school_year',
#             'admission_date', 'previous_school_name', 'previous_standard_studied',
#             'tc_letter', 'emergency_contact_no', 'entire_road_distance_from_home_to_school',
#             'obtain_marks', 'total_marks', 'previous_percentage','enrollment_no','is_rte', 'rte_number'
#         ]
#         read_only_fields = [
#             'admission_date',
#             'student_input',
#             'guardian_input',
#             'guardian_type',
#             'address',
#             'banking_detail',
#             'enrollment_no'
#         ]

#     def get_student_input(self, obj):
#         if obj.student:
#             return StudentSerializer(obj.student).data
#         return None

#     def get_guardian_input(self, obj):
#         if obj.guardian:
#             return GuardianSerializer(obj.guardian).data
#         return None

#     def get_address(self, obj):
#         address = Address.objects.filter(user=obj.student.user).first()
#         return AddressSerializer(address).data if address else None

#     def get_banking_detail(self, obj):
#         banking = BankingDetail.objects.filter(user=obj.student.user).first()
#         return BankingDetailsSerializer(banking).data if banking else None

#     def get_guardian_type(self, obj):
#         try:
#             sg = StudentGuardian.objects.get(student=obj.student, guardian=obj.guardian)
#             return sg.guardian_type.name
#         except StudentGuardian.DoesNotExist:
#             return None

#     def create(self, validated_data):
#         is_rte = validated_data.pop('is_rte', False)
#         rte_number = validated_data.pop('rte_number', None)
#         student_data = validated_data.pop('student')
#         guardian_data = validated_data.pop('guardian')
#         address_data = validated_data.pop('address_input', None)
#         banking_data = validated_data.pop('banking_detail_input', None)
#         guardian_type = validated_data.pop('guardian_type_input', None)
#         year_level = validated_data.pop('year_level', None)
#         school_year = validated_data.pop('school_year', None)

#         # --- Student processing ---
#         classes_data = student_data.pop('classes', [])
#         if isinstance(classes_data, str):
#             try:
#                 classes_data = [int(classes_data)]
#             except ValueError:
#                 raise serializers.ValidationError({"student.classes": "Invalid class ID format."})

#         user_data = {
#             'first_name': student_data.pop('first_name', ''),
#             'middle_name': student_data.pop('middle_name', ''),
#             'last_name': student_data.pop('last_name', ''),
#             'email': student_data.pop('email'),
#             'password': student_data.pop('password', None),
#             'user_profile': student_data.pop('user_profile', None),
#         }

#         user = User.objects.filter(email__iexact=user_data['email']).first()
#         if not user:
#             role, _ = Role.objects.get_or_create(name='student')
#             user = User.objects.create_user(**user_data)
#             user.role.add(role)

#         student, created = Student.objects.get_or_create(user=user, defaults=student_data)
#         if not created:
#             raise serializers.ValidationError({"student": "Student already exists for this user."})

#         if classes_data:
#             student.classes.set(classes_data)

#         # --- Address and banking ---
#         if address_data:
#             Address.objects.update_or_create(user=user, defaults=address_data)
#         if banking_data:
#             BankingDetail.objects.update_or_create(user=user, defaults=banking_data)

#         # --- Guardian user creation ---
#         guardian_user_data = {
#             'first_name': guardian_data.pop('first_name', ''),
#             'middle_name': guardian_data.pop('middle_name', ''),
#             'last_name': guardian_data.pop('last_name', ''),
#             'email': guardian_data.pop('email'),
#             'password': guardian_data.pop('password', None),
#             'user_profile': guardian_data.pop('user_profile', None),
#         }

#         guardian_user = User.objects.filter(email__iexact=guardian_user_data['email']).first()
#         if not guardian_user:
#             role, _ = Role.objects.get_or_create(name='guardian')
#             guardian_user = User.objects.create_user(**guardian_user_data)
#             guardian_user.role.add(role)
#         else:
#             for attr, value in guardian_user_data.items():
#                 if value:
#                     setattr(guardian_user, attr, value)
#             guardian_user.save()

#         # --- Guardian model creation or update ---
#         guardian, _ = Guardian.objects.get_or_create(user=guardian_user, defaults=guardian_data)
#         if guardian_data:
#             guardian_serializer = GuardianSerializer(guardian, data=guardian_data, partial=True)
#             guardian_serializer.is_valid(raise_exception=True)
#             guardian_serializer.save()

#         # --- Admission creation ---
#         admission = Admission.objects.create(
#             student=student,
#             guardian=guardian,
#             previous_school_name=validated_data.get('previous_school_name'),
#             previous_standard_studied=validated_data.get('previous_standard_studied'),
#             tc_letter=validated_data.get('tc_letter'),
#             year_level=year_level,
#             school_year=school_year,
#             emergency_contact_no=validated_data.get('emergency_contact_no'),
#             entire_road_distance_from_home_to_school=validated_data.get('entire_road_distance_from_home_to_school'),
#             obtain_marks=validated_data.get('obtain_marks'),
#             total_marks=validated_data.get('total_marks'),
#             previous_percentage=validated_data.get('previous_percentage'),
#             enrollment_no=validated_data.get('enrollment_no'),
#             is_rte=is_rte,
#             rte_number=rte_number

#         )

#         if guardian_type:
#             StudentGuardian.objects.update_or_create(
#                 student=student, guardian=guardian, defaults={'guardian_type': guardian_type}
#             )

#         if year_level and school_year:
#             StudentYearLevel.objects.update_or_create(
#                 student=student, level=year_level, year=school_year
#             )

#         return admission


#     def update(self, instance, validated_data):
#         instance.is_rte = validated_data.get('is_rte', instance.is_rte)
#         instance.rte_number = validated_data.get('rte_number', instance.rte_number)
#         student_data = validated_data.pop('student', None)
#         guardian_data = validated_data.pop('guardian', None)
#         address_data = validated_data.pop('address_input', None)
#         banking_data = validated_data.pop('banking_detail_input', None)
#         guardian_type = validated_data.pop('guardian_type_input', None)
#         year_level = validated_data.pop('year_level', None)
#         school_year = validated_data.pop('school_year', None)

#         user = self.context.get("user") or instance.student.user

#         if student_data:
#             student_serializer = StudentSerializer(instance.student, data=student_data, partial=True)
#             student_serializer.is_valid(raise_exception=True)
#             student_serializer.save()

#             classes_data = student_data.get('classes')
#             if isinstance(classes_data, str):
#                 try:
#                     classes_data = [int(classes_data)]
#                 except ValueError:
#                     raise serializers.ValidationError({"student.classes": "Invalid class ID format."})

#             if classes_data:
#                 instance.student.classes.set(classes_data)

#         if guardian_data:
#             guardian_serializer = GuardianSerializer(instance.guardian, data=guardian_data, partial=True)
#             guardian_serializer.is_valid(raise_exception=True)
#             guardian_serializer.save()

#         if address_data:
#             for key in ['city', 'state', 'country']:
#                 val = address_data.get(key)
#                 if hasattr(val, 'id'):
#                     address_data[key] = val.id

#             try:
#                 address_instance = Address.objects.get(user=user)
#                 address_serializer = AddressSerializer(address_instance, data=address_data, partial=True)
#             except Address.DoesNotExist:
#                 address_serializer = AddressSerializer(data=address_data)

#             address_serializer.is_valid(raise_exception=True)
#             address_serializer.save(user=user)

#         if banking_data:
#             current_account_no = str(banking_data.get('account_no'))

#             try:
#                 banking_instance = BankingDetail.objects.get(user=user)
#                 existing_account_no = str(banking_instance.account_no)

#                 if existing_account_no == current_account_no:
#                     banking_data.pop('account_no', None)
#                 else:
#                     if BankingDetail.objects.filter(account_no=current_account_no).exclude(user_id=user.id).exists():
#                         raise serializers.ValidationError({
#                             "banking_detail_input": {
#                                 "account_no": ["This account number is already in use by another user."]
#                             }
#                         })

#                 banking_serializer = BankingDetailsSerializer(banking_instance, data=banking_data, partial=True)
#                 banking_serializer.is_valid(raise_exception=True)
#                 banking_serializer.save(user=user)

#             except BankingDetail.DoesNotExist:
#                 if BankingDetail.objects.filter(account_no=current_account_no).exists():
#                     raise serializers.ValidationError({
#                         "banking_detail_input": {
#                             "account_no": ["This account number is already in use."]
#                         }
#                     })

#                 banking_serializer = BankingDetailsSerializer(data=banking_data)
#                 banking_serializer.is_valid(raise_exception=True)
#                 banking_serializer.save(user=user)

#         if guardian_type:
#             StudentGuardian.objects.update_or_create(
#                 student=instance.student,
#                 guardian=instance.guardian,
#                 defaults={"guardian_type": guardian_type}
#             )

#         if year_level:
#             instance.year_level = year_level
#         if school_year:
#             instance.school_year = school_year

#         for attr, value in validated_data.items():
#             setattr(instance, attr, value)

#         instance.save()
#         return instance













# **********Assignment ClassPeriod for Student behalf of YearLevel(Standard)********************

# As of 05May25 at 01:00 PM


# class ClassPeriodSerializer(serializers.ModelSerializer):
#     # Extra fields for the custom POST action
#     year_level_name = serializers.CharField(write_only=True, required=False)
#     class_period_names = serializers.ListField(
#         child=serializers.CharField(), write_only=True, required=False
#     )

#     class Meta:
#         model = ClassPeriod
#         fields = [
#             'id', 'subject', 'teacher', 'term',
#             'start_time', 'end_time', 'classroom', 'name',
#             'year_level', 'year_level_name', 'class_period_names'
#         ]

#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         representation['start_time'] = instance.start_time.start_period_time.strftime('%I:%M %p')
#         representation['end_time'] = instance.end_time.end_period_time.strftime('%I:%M %p')
#         return representation

#     def create(self, validated_data):
#         # Handle assignment logic only if year_level_name and class_period_names are present
#         year_level_name = validated_data.pop('year_level_name', None)
#         class_period_names = validated_data.pop('class_period_names', None)

#         if year_level_name and class_period_names:
#             try:
#                 year_level = YearLevel.objects.get(level_name=year_level_name)
#             except YearLevel.DoesNotExist:
#                 raise serializers.ValidationError("Invalid YearLevel name.")

#             class_periods = ClassPeriod.objects.filter(name__in=class_period_names)
#             if class_periods.count() != len(class_period_names):
#                 raise serializers.ValidationError("Some ClassPeriod names are invalid.")

#             student_ids = StudentYearLevel.objects.filter(level=year_level).values_list("student_id", flat=True)
#             students = Student.objects.filter(id__in=student_ids)

#             for student in students:
#                 student.classes.add(*class_periods)

#             return {
#                 "students_updated": students.count(),
#                 "class_periods_assigned": [cp.name for cp in class_periods]
#             }

#         # If not an assignment request, create a regular ClassPeriod (fallback)
#         return super().create(validated_data)

# class ClassPeriodSerializer(serializers.ModelSerializer):     just commeented as of 20Aug25
#     # Extra fields for the custom POST action
#     year_level_name = serializers.CharField(write_only=True, required=False)
#     class_period_names = serializers.ListField(
#         child=serializers.CharField(), write_only=True, required=False
#     )

#     class Meta:
#         model = ClassPeriod
#         fields = [
#             'id', 'subject', 'teacher', 'term',
#             'start_time', 'end_time', 'classroom', 'name',
#             'year_level', 'year_level_name', 'class_period_names'
#         ]


class ClassPeriodSerializer(serializers.ModelSerializer):
    # Alias: accept `year_level_id` instead of `year_level`
    yearlevel_id = serializers.PrimaryKeyRelatedField(
        source="year_level",  # map it to the actual FK
        queryset=YearLevel.objects.all(),
        write_only=True
    )

    year_level = serializers.PrimaryKeyRelatedField(read_only=True)  # still return year_level in response

    # Extra fields for the custom POST action
    year_level_name = serializers.CharField(write_only=True, required=False)
    class_period_names = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    class Meta:
        model = ClassPeriod
        fields = [
            'id', 'subject', 'teacher', 'term',
            'start_time', 'end_time', 'classroom', 'name',
            'year_level', 'yearlevel_id',  # include both
            'year_level_name', 'class_period_names'
        ]


    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['start_time'] = instance.start_time.start_period_time.strftime('%I:%M %p')
        representation['end_time'] = instance.end_time.end_period_time.strftime('%I:%M %p')
        return representation

    def validate(self, attrs):
        teacher = attrs.get('teacher')
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')

        if teacher and start_time and end_time:
            overlapping = ClassPeriod.objects.filter(
                teacher=teacher,
                start_time__lt=end_time,
                end_time__gt=start_time,
            )

            if self.instance:
                overlapping = overlapping.exclude(id=self.instance.id)

            if overlapping.exists():
                raise serializers.ValidationError(
                    {"non_field_errors": ["This teacher is already assigned to another class during this time."]}
                )

        return attrs

    def create(self, validated_data):
        # Handle assignment logic only if year_level_name and class_period_names are present
        year_level_name = validated_data.pop('year_level_name', None)
        class_period_names = validated_data.pop('class_period_names', None)

        if year_level_name and class_period_names:
            try:
                year_level = YearLevel.objects.get(level_name=year_level_name)
            except YearLevel.DoesNotExist:
                raise serializers.ValidationError("Invalid YearLevel name.")

            class_periods = ClassPeriod.objects.filter(name__in=class_period_names)
            if class_periods.count() != len(class_period_names):
                raise serializers.ValidationError("Some ClassPeriod names are invalid.")

            student_ids = StudentYearLevel.objects.filter(level=year_level).values_list("student_id", flat=True)
            students = Student.objects.filter(id__in=student_ids)

            for student in students:
                student.classes.add(*class_periods)

            return {
                "students_updated": students.count(),
                "class_periods_assigned": [cp.name for cp in class_periods]
            }

        # If not an assignment request, create a regular ClassPeriod (fallback)
        return super().create(validated_data)




# Added as of 06June25 at 02:50 PM

class FeeTypeSerializer(serializers.ModelSerializer):
    # name = serializers.SerializerMethodField()
    
    class Meta:
        model = FeeType
        fields = ['id', 'name']


class YearLevelFeeSerializer(serializers.ModelSerializer):
    year_level_name = serializers.SerializerMethodField()
    fee_type_name = serializers.SerializerMethodField()
    year_level_id = serializers.IntegerField(source='year_level.id', read_only=True)
    final_amount = serializers.SerializerMethodField()
    # original_amount = serializers.DecimalField(source="amount", max_digits=8, decimal_places=2, read_only=True)


    class Meta:
        model = YearLevelFee
        fields = ['id', 'year_level', 'fee_type', 'year_level_name', 'fee_type_name', 'amount',
            'final_amount', 'year_level_id']

    def get_year_level_name(self, obj):
        return obj.year_level.level_name

    def get_fee_type_name(self, obj):
        return obj.fee_type.name

    
    
    # def to_representation(self, instance):        # just commented as of 26Aug25
    #     data = super().to_representation(instance)
    #     data.pop('year_level', None)
    #     data.pop('fee_type', None)
    #     return data
    
    def to_representation(self, instance):          # Added as of 26Aug25 at 01:30 PM
        data = super().to_representation(instance)
        data.pop('year_level', None)
        data.pop('fee_type', None)
        
        # Ensure amount and final_amount are properly formatted as strings with 2 decimal places
        data['amount'] = str(Decimal(data['amount']).quantize(Decimal('0.00')))
        data['final_amount'] = str(Decimal(data['final_amount']).quantize(Decimal('0.00')))
        
        return data
    
    

    # def get_final_amount(self, obj):
    #     student = self.context.get("student")
    #     final_amount = obj.amount
    #     fee_type = obj.fee_type.name.lower()

    #     if student:
    #         discount = FeeDiscount.objects.filter(student=student, is_allowed=True).first()
    #         fee_type = obj.fee_type.name.lower()

    #         if discount:
    #             if "admission fee" in fee_type and discount.admission_fee_discount:
    #                 final_amount = obj.amount - discount.admission_fee_discount
    #             if "tuition fee" in fee_type and discount.tuition_fee_discount:
    #                 final_amount = obj.amount - discount.tuition_fee_discount

    #     return str(final_amount)                  # just commented as of 26Aug25 at 11:53 AM
    
    # Added as of 26Aug25 at 11:53 AM
    def get_final_amount(self, obj):
        student = self.context.get("student")
        final_amount = obj.amount
        fee_type = obj.fee_type.name.lower()

        if student:
            discount = FeeDiscount.objects.filter(student=student, is_allowed=True).first()
            fee_type = obj.fee_type.name.lower()

            if discount:
                if "admission fee" in fee_type and discount.admission_fee_discount:
                    final_amount = obj.amount - discount.admission_fee_discount
                if "tuition fee" in fee_type and discount.tuition_fee_discount:
                    final_amount = obj.amount - discount.tuition_fee_discount

        # Return as Decimal instead of string
        return final_amount

    
    
    def get_year_level_fees_grouped(self, obj):
        grouped = defaultdict(list)

        # fetch fee discount for this student if allowed
        discount = FeeDiscount.objects.filter(student=obj.student, is_allowed=True).first()

        for fee in obj.year_level_fees.all():
            year_level_name = fee.year_level.level_name
            fee_type = fee.fee_type.name.lower()
            fee_amount = fee.amount

            # FIXED: Always show original amount
            final_amount = fee_amount  

            if discount:
                # if it's admission fee and student has a discounted admission_fee saved in FeeDiscount
                if "admission fee" in fee_type:
                    final_amount = fee_amount - (discount.admission_fee_discount or 0)  # highlighted
                # if it's tuition fee and student has a discounted tuition_fee saved in FeeDiscount
                if "tuition fee" in fee_type:
                    final_amount = fee_amount - (discount.tuition_fee_discount or 0)  # highlighted

            # FIXED: Always send amount and final_amount
            grouped[year_level_name].append({
                "id": fee.id,
                "fee_type": fee.fee_type.name,
                "amount": str(fee_amount),  # original amount
                "final_amount": str(final_amount),  # discounted/final amount
            })

        return [{"year_level": yl, "fees": fees} for yl, fees in grouped.items()]


 
    # Added this as of 11June25 at 11:39 AM
    @staticmethod
    def group_by_year_level(fees):
        grouped_fees = {}
        for fee in fees:
            year_level_name = fee['year_level_name']
            year_level_id = fee['year_level_id']
            fee_data = {
                'id': fee['id'],
                'fee_type': fee['fee_type_name'],
                'amount': fee['amount'],
                'final_amount': fee['final_amount'],
            }

            # Use a tuple key to keep both id and name
            key = (year_level_id, year_level_name)

            if key not in grouped_fees:
                grouped_fees[key] = {
                    'id': year_level_id,
                    'year_level': year_level_name,
                    'fees': []
                }

            grouped_fees[key]['fees'].append(fee_data)

        return list(grouped_fees.values())


# class FeeDiscountSerializer(serializers.ModelSerializer):         # commented today as of 26Aug25 at 09:53 AM
#     student_id = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(),source='student')
#     student_name = serializers.SerializerMethodField()

#     class Meta:
#         model = FeeDiscount
#         fields = ["id","student_id","student_name","admission_fee_discount","tuition_fee_discount","admission_fee","tuition_fee","discount_reason","is_allowed","created_at","updated_at",]
#         read_only_fields = ["admission_fee","tuition_fee","created_at", "updated_at"]  
    
#     def get_student_name(self, obj):
#         return f"{obj.student.user.first_name} {obj.student.user.last_name}".strip()

class FeeDiscountSerializer(serializers.ModelSerializer):   # added today as of 26Aug25 at 09:53 AM to add class
    student_id = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(),source='student')
    student_name = serializers.SerializerMethodField()
    year_level = serializers.SerializerMethodField()
    scholar_no = serializers.SerializerMethodField()

    class Meta:
        model = FeeDiscount
        fields = ["id","student_id","student_name","scholar_no","year_level","admission_fee_discount","tuition_fee_discount","admission_fee","tuition_fee","discount_reason","is_allowed","created_at","updated_at",]
        read_only_fields = ["admission_fee","tuition_fee","created_at", "updated_at","scholar_no"]  
    
    def get_student_name(self, obj):
        return f"{obj.student.user.first_name} {obj.student.user.last_name}".strip()

    def get_year_level(self, obj):
        student_year_level = (
            StudentYearLevel.objects
            .filter(student=obj.student)
            .order_by('-year')  # if multiple, get the latest
            .first()
        )
        return student_year_level.level.level_name if student_year_level else None

    def get_scholar_no(self, obj):
        scholar_no= obj.student.scholar_number
        return scholar_no

    def validate(self, attrs):
        student = attrs.get("student")

        # On create: block if any existing record for this student
        if self.instance is None and FeeDiscount.objects.filter(student=student).exists():
            raise serializers.ValidationError(
                {"student_id": f"A discount already exists for this student."}
            )

        # On update: block if trying to assign to another student that already has a discount
        if self.instance and student != self.instance.student:
            if FeeDiscount.objects.filter(student=student).exists():
                raise serializers.ValidationError(
                    {"student_id": f"A discount already exists for this student."}
                )
        # Get student's year level current)
        student_year_level = (
            StudentYearLevel.objects
            .filter(student=student)
            .order_by('-year')  # if multiple, get the latest
            .first()
        )

        if not student_year_level:
            raise serializers.ValidationError({
                "student_id": "No year level found for this student."
            })

        # Get actual fees for student's class/year level
        admission_fee = (
            YearLevelFee.objects
            .filter(year_level=student_year_level.level, fee_type__name__icontains="admission fee")
            .first()
        )
        tuition_fee = (
            YearLevelFee.objects
            .filter(year_level=student_year_level.level, fee_type__name__icontains="tuition fee")
            .first()
        )

        admission_fee_amount = Decimal(admission_fee.amount) if admission_fee else Decimal("0")
        tuition_fee_amount = Decimal(tuition_fee.amount) if tuition_fee else Decimal("0")

        admission_discount = Decimal(attrs.get("admission_fee_discount") or 0)
        tuition_discount = Decimal(attrs.get("tuition_fee_discount") or 0)

        errors = {}

        if admission_discount > admission_fee_amount:
            errors["admission_fee_discount"] = (
                f"Cannot exceed actual admission fee ({admission_fee_amount})."
            )

        if tuition_discount > tuition_fee_amount:
            errors["tuition_fee_discount"] = (
                f"Cannot exceed actual tuition fee ({tuition_fee_amount})."
            )
        
        attrs["admission_fee"] = admission_fee_amount - admission_discount
        attrs["tuition_fee"] = tuition_fee_amount - tuition_discount

        if errors:
            raise serializers.ValidationError(errors)
        return attrs


### just added to submit fee for multiple months as of 09Jun25 at 06:53 PM
class FeeRecordSerializer(serializers.ModelSerializer):
    student = serializers.SerializerMethodField()
    student_id = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), source='student', write_only=True)
    year_level_fees = serializers.PrimaryKeyRelatedField(queryset=YearLevelFee.objects.all(), many=True, write_only=True)
    year_level_fees_grouped = serializers.SerializerMethodField(read_only=True)
    discounted_amount = serializers.SerializerMethodField()
    total_amount = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    paid_amount = serializers.DecimalField(max_digits=8, decimal_places=2)
    due_amount = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    late_fee = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    payment_date = serializers.DateField(read_only=True)
    receipt_number = serializers.CharField(read_only=True)
    payment_status = serializers.CharField(max_length=20, read_only=True)
    remarks = serializers.CharField(max_length=255, required=False, allow_null=True)
    received_by = serializers.CharField(max_length=100,required=False, allow_null=True)
    payment_mode = serializers.ChoiceField(choices=FeeRecord._meta.get_field('payment_mode').choices)
    month = serializers.ChoiceField(choices=FeeRecord.MONTH_CHOICES)
    school_year = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = FeeRecord
        fields = [
            'id', 'student', 'student_id', 'month', 'school_year', 'year_level_fees', 'year_level_fees_grouped',
            'total_amount', 'paid_amount', 'due_amount','discounted_amount', 'payment_date', 'payment_mode', 'is_cheque_cleared','receipt_number',
            'late_fee', 'payment_status', 'remarks', 'received_by'
        ]
        read_only_fields = ['receipt_number', 'payment_date', 'total_amount', 'due_amount', 'late_fee']

    def get_student(self, obj):
        return {
            "id": obj.student.id,
            "name": f"{obj.student.user.first_name} {obj.student.user.last_name}"
        }

    def get_school_year(self, obj):
        if obj.school_year and obj.school_year.year:
            return obj.school_year.year.year_name
        return None
    
    def get_discounted_amount(self, obj):
        admission_discount = 0
        tuition_discount = 0

        try:
            discount = FeeDiscount.objects.get(student=obj.student, is_allowed=True)
        except FeeDiscount.DoesNotExist:
            return "0.00"

        for fee in obj.year_level_fees.all():
            fee_type = fee.fee_type.name.lower()
            if "admission fee" in fee_type and discount.admission_fee_discount:
                admission_discount += float(discount.admission_fee_discount)
            if "tuition fee" in fee_type and discount.tuition_fee_discount:
                tuition_discount += float(discount.tuition_fee_discount)

        return {"admission discount":f"{admission_discount:.2f}",
                "tuition discount":f"{tuition_discount:.2f}"}
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = self.context['request'].user

        # Check role
        roles = user.role.values_list("name", flat=True)

        if "director" not in roles and "student" not in roles:
            data.pop("discounted_amount", None)# hide it from non-directors or students

        return data
    

    def get_year_level_fees_grouped(self, obj):
        grouped = defaultdict(list)

        #  fetch fee discount for this student if allowed
        discount = FeeDiscount.objects.filter(student=obj.student, is_allowed=True).first()

        for fee in obj.year_level_fees.all():
            year_level_name = fee.year_level.level_name
            fee_type = fee.fee_type.name.lower()
            fee_amount = fee.amount

            # default: use original amount
            final_amount = fee_amount  

            if discount:
                # if it's admission fee and student has a discounted admission_fee saved in FeeDiscount
                if "admission fee" in fee_type and discount.admission_fee and discount.admission_fee != 0:
                    final_amount = discount.admission_fee

                # if it's tuition fee and student has a discounted tuition_fee saved in FeeDiscount
                if "tuition fee" in fee_type and discount.tuition_fee and discount.tuition_fee != 0:
                    final_amount = discount.tuition_fee

            grouped[year_level_name].append({
                "id": fee.id,
                "fee_type": fee.fee_type.name,
                "amount": str(final_amount),
            })

        return [{"year_level": yl, "fees": fees} for yl, fees in grouped.items()]


    def validate(self, data):
        student = data.get('student')
        month = data.get('month')
        year_level_fees = data.get('year_level_fees', [])
        paid_amount = data.get('paid_amount', 0)

        if not year_level_fees:
            raise serializers.ValidationError("At least one year level fee must be selected.")

        # Fetch any allowed discount for this student
        try:
            discount = FeeDiscount.objects.get(student=student, is_allowed=True)
        except FeeDiscount.DoesNotExist:
            discount = None

        total_amount = 0
        tuition_due = 0
        tuition_fee_obj = None
        non_tuition_total = 0

        # First pass: calculate final amounts and detect tuition fee
        for fee in year_level_fees:
            fee_name = fee.fee_type.name.lower()
            fee_amount = fee.amount
            fee_discount = 0

            # Apply discount
            if discount:
                if "tuition fee" in fee_name:
                    fee_discount = discount.tuition_fee_discount or 0
                elif "admission fee" in fee_name:
                    fee_discount = discount.admission_fee_discount or 0

            final_fee_amount = max(fee_amount - fee_discount, 0)
            fee.final_amount = final_fee_amount  # optional, store for later
            total_amount += final_fee_amount

            if "tuition fee" in fee_name:
                tuition_fee_obj = fee
            else:
                non_tuition_total += final_fee_amount

            # ADMISSION: one-time, no dues
            if "admission fee" in fee_name:
                if FeeRecord.objects.filter(student=student, year_level_fees=fee).exists():
                    raise serializers.ValidationError({
                        "admission_fee": "Admission fee already paid for this student."
                    })

            # Non-tuition fees: must be fully paid
            if "tuition fee" not in fee_name:
                if paid_amount < final_fee_amount:
                    raise serializers.ValidationError({
                        fee_name.replace(" ", "_"): f"{fee.fee_type.name} must be paid in full. Partial payments not allowed."
                    })
                if FeeRecord.objects.filter(student=student, month=month, year_level_fees=fee).exists():
                    raise serializers.ValidationError({
                        fee_name.replace(" ", "_"): f"{fee.fee_type.name} of {month} already submitted."
                    })

        # Late fee only for tuition
        today = date.today()
        late_fee = 0
        if tuition_fee_obj and today.day > 15:
            late_fee = 25
            total_amount += late_fee
        data['late_fee'] = late_fee

        # Tuition due calculation
        if tuition_fee_obj:
            tuition_final_amount = tuition_fee_obj.amount - (discount.tuition_fee_discount if discount else 0)
            existing_tuition = FeeRecord.objects.filter(
                student=student,
                month=month,
                year_level_fees=tuition_fee_obj
            ).order_by("-id").first()
            paid_so_far = existing_tuition.paid_amount if existing_tuition else 0
            remaining_due = max(tuition_final_amount - paid_so_far, 0)
            if today.day > 15:
                late_fee = 25
                remaining_due += late_fee
            # print("paid_so_far:",paid_so_far)
            # print("remaining_due:",remaining_due)

            if existing_tuition:
                data['total_amount'] = remaining_due
            else:
                data['total_amount'] = tuition_final_amount + (25 if today.day > 15 else 0)


            # Check if non-tuition fees are in the same payment
            non_tuition_present = any("tuition fee" not in f.fee_type.name.lower() for f in year_level_fees)

            if non_tuition_present:
                # Tuition must be fully paid if paying with non-tuition fees
                if paid_amount < remaining_due + non_tuition_total:
                    raise serializers.ValidationError({
                        "tuition_fee": f"Tuition must be fully paid when paying with other fees. {remaining_due} is due."
                    })
                tuition_payment = remaining_due
            else:
                # Tuition alone → partial allowed
                tuition_payment = min(paid_amount, remaining_due)

            tuition_due = remaining_due - tuition_payment
            # print("tuition_due:",tuition_due)

            if FeeRecord.objects.filter(
                student=student,
                month=month,
                year_level_fees=tuition_fee_obj,
                payment_status="Paid"
            ).exists():
                raise serializers.ValidationError({
                    "tuition_fee": f"Tuition fee for {month} is already fully paid."
                })

            # Must pay exact due (not less / not more)
            if existing_tuition:
                # calc remaining
                remaining_due = max(tuition_final_amount - existing_tuition.paid_amount, 0)
                if today.day > 15:
                    late_fee = 25
                    remaining_due += late_fee

                # force total_amount to equal remaining_due
                data["total_amount"] = remaining_due

                # must pay exact remaining due if clearing
                if paid_amount != remaining_due:
                    raise serializers.ValidationError({
                        "tuition_fee": f"You must pay the exact due amount: {remaining_due}."
                    })

        else:
            tuition_due = 0

    
        # Set final totals
        data['total_amount'] = total_amount
        data['due_amount'] = tuition_due

        # Payment status
        if tuition_fee_obj:
            if tuition_due == 0 and paid_amount > 0:
                data['payment_status'] = "Paid"
            elif tuition_due > 0 and paid_amount > 0:
                data['payment_status'] = "Partially Paid"
            else:
                data['payment_status'] = "Unpaid"
        else:
            # Non-tuition only
            data['payment_status'] = "Paid" if paid_amount > 0 else "Unpaid"

        # Paid amount validation
        if paid_amount > total_amount:
            raise serializers.ValidationError(
                f"Paid amount {paid_amount} cannot exceed total amount {total_amount}."
            )

        return data
  

    ### Added this as of 11June25 at 01:39 PM
    def create(self, validated_data):
        year_level_fees = validated_data.pop('year_level_fees')
        validated_data['payment_date'] = date.today()

        # total_amount = validated_data.get('total_amount', 0)
        # paid_amount = validated_data.get('paid_amount', 0)
        # late_fee = validated_data.get('late_fee', 0)
        # due_amount = validated_data.get('due_amount', 0)
        # payment_mode = validated_data.get('payment_mode')
        # is_cheque_cleared = validated_data.get('is_cheque_cleared', False)
        student = validated_data.get("student")

                
        # get student's latest StudentYearLevel (adjust ordering logic if needed)
        student_year_level = student.student_year_levels.order_by("-year__start_date").first()
        if student_year_level:
            validated_data["school_year"] = student_year_level  

        # # Default status
        # payment_status = 'Unpaid'
        
        # if payment_mode == 'Cash' or payment_mode == 'Online':
        #     if paid_amount >= total_amount :
        #         payment_status = 'Paid'
        # elif payment_mode == 'Cheque':
        #     if is_cheque_cleared and paid_amount >= total_amount:
        #         payment_status = 'Paid'
        #     else:
        #         payment_status = 'Unpaid'
        
        # validated_data['payment_status'] = payment_status

        fee_record = FeeRecord.objects.create(**validated_data)
        fee_record.year_level_fees.set(year_level_fees)
        return fee_record


# class FeeRecordRazorpaySerializer(serializers.ModelSerializer):
#     student_id = serializers.PrimaryKeyRelatedField(
#         queryset=Student.objects.all(), source='student', write_only=True
#     )
#     year_level_fees = serializers.PrimaryKeyRelatedField(
#         queryset=YearLevelFee.objects.all(),
#         many=True,
#         required=False,
#         default=[]
#     )
#     receipt_number = serializers.CharField(read_only=True)
#     paid_amount = serializers.DecimalField(max_digits=10, decimal_places=2)

#     class Meta:
#         model = FeeRecord
#         fields = [
#             'id', 'student_id', 'month', 'year_level_fees', 'total_amount', 'paid_amount',
#             'due_amount', 'late_fee', 'payment_mode', 'payment_status', 'remarks', 'received_by',
#             'razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature_id', 'receipt_number'
#         ]
#         read_only_fields = [
#             'total_amount', 'due_amount', 'late_fee', 'payment_status',
#             'razorpay_payment_id', 'razorpay_signature_id', 'receipt_number'
#         ]

#     def validate(self, data):
#         student = data.get('student')
#         year_level_fees = data.get('year_level_fees', [])
#         paid_amount = data.get('paid_amount', Decimal("0.00"))
#         payment_mode = data.get('payment_mode', '').lower()
        
#         if isinstance(paid_amount, str):
#             paid_amount = Decimal(paid_amount)
    
#         # Online payment validation
#         if payment_mode == 'online' and paid_amount <= 0:
#             raise serializers.ValidationError("Paid amount must be greater than 0 for online payment.")

#         # Calculate total from selected fees
#         base_total = sum(fee.amount for fee in year_level_fees) if year_level_fees else Decimal("0.00")

#         # Apply discount
#         try:
#             discount = FeeDiscount.objects.get(student=student, is_allowed=True)
#         except FeeDiscount.DoesNotExist:
#             discount = None

#         total_discount = Decimal("0.00")
#         if discount:
#             for fee in year_level_fees:
#                 fee_type = fee.fee_type.name.lower()
#                 if "admission fee" in fee_type:
#                     total_discount += discount.admission_fee_discount or Decimal("0.00")
#                 if "tuition fee" in fee_type:
#                     total_discount += discount.tuition_fee_discount or Decimal("0.00")

#         discounted_total = max(base_total - total_discount, Decimal("0.00"))

#         # Late fee calculation
#         today = date.today()
#         late_fee = Decimal("0.00")
#         if any("tuition fee" in fee.fee_type.name.lower() for fee in year_level_fees) and today.day > 15:
#             late_fee = Decimal("25.00")

#         total = discounted_total + late_fee

#         # Allow partial payment
#         due_amount = max(total - paid_amount, Decimal("0.00"))

#         data['total_amount'] = discounted_total
#         data['late_fee'] = late_fee
#         data['due_amount'] = due_amount
#         data['paid_amount'] = paid_amount

#         # FIXED: PROPER STATUS CALCULATION FOR ONLINE PAYMENTS
#         if payment_mode == 'online':
#             # For online payments, status should be based on paid_amount vs total
#             if paid_amount >= total:
#                 data['payment_status'] = 'Paid'
#             elif paid_amount > 0:
#                 data['payment_status'] = 'Partially Paid'
#             else:
#                 data['payment_status'] = 'Unpaid'
#         else:
#             # Cash payment logic remains same
#             if due_amount == 0 and paid_amount > 0:
#                 data['payment_status'] = 'Paid'
#             elif paid_amount > 0:
#                 data['payment_status'] = 'Partially Paid'
#             else:
#                 data['payment_status'] = 'Unpaid'

#         # Razorpay fields
#         if 'razorpay_order_id' in self.initial_data:
#             data['razorpay_order_id'] = self.initial_data.get('razorpay_order_id')
#         if 'razorpay_payment_id' in self.initial_data:
#             data['razorpay_payment_id'] = self.initial_data.get('razorpay_payment_id')
#         if 'razorpay_signature_id' in self.initial_data:
#             data['razorpay_signature_id'] = self.initial_data.get('razorpay_signature_id')

#         print(f"DEBUG: Payment Mode: {payment_mode}, Status: {data.get('payment_status')}")
#         return data

#     def create(self, validated_data):
#         year_level_fees = validated_data.pop('year_level_fees', [])
        
#         #  FIXED: Ensure status is preserved
#         fee_record = FeeRecord.objects.create(**validated_data)
#         fee_record.year_level_fees.set(year_level_fees)

#         # Generate receipt number if not exists
#         if not fee_record.receipt_number:
#             fee_record.receipt_number = self.generate_unique_receipt_number()
#             fee_record.save()

#         print(f"DEBUG: Final Status Saved: {fee_record.payment_status}")
#         return fee_record

#     def generate_unique_receipt_number(self):
#         today = datetime.now().strftime('%Y%m%d')
#         last_receipt = FeeRecord.objects.filter(receipt_number__startswith=f'REC-{today}') \
#                                         .aggregate(Max('receipt_number'))
#         if last_receipt['receipt_number__max']:
#             last_number = int(last_receipt['receipt_number__max'].split('-')[-1])
#             new_number = last_number + 1
#         else:
#             new_number = 1
#         return f'REC-{today}-{new_number:05d}'

class FeeRecordRazorpaySerializer(serializers.ModelSerializer):
    student_id = serializers.PrimaryKeyRelatedField(
        queryset=Student.objects.all(), source='student', write_only=True
    )
    year_level_fees = serializers.PrimaryKeyRelatedField(
        queryset=YearLevelFee.objects.all(),
        many=True,
        required=False,
        default=[]
    )
    receipt_number = serializers.CharField(read_only=True)
    paid_amount = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = FeeRecord
        fields = [
            'id', 'student_id', 'month', 'year_level_fees', 'total_amount', 'paid_amount',
            'due_amount', 'late_fee', 'payment_mode', 'payment_status', 'remarks', 'received_by',
            'razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature_id', 'receipt_number'
        ]
        read_only_fields = [
            'total_amount', 'due_amount', 'late_fee', 'payment_status',
            'razorpay_payment_id', 'razorpay_signature_id', 'receipt_number'
        ]

    def validate(self, data):
        student = data.get('student')
        year_level_fees = data.get('year_level_fees', [])
        paid_amount = data.get('paid_amount', Decimal("0.00"))
        payment_mode = data.get('payment_mode', '').lower()
        
        if isinstance(paid_amount, str):
            paid_amount = Decimal(paid_amount)
    
       
        if payment_mode == 'online' and paid_amount <= 0:
            raise serializers.ValidationError("Paid amount must be greater than 0 for online payment.")
        
        year_level_fees_ids = self.initial_data.get('year_level_fees', [])
        year_level_fees_qs = YearLevelFee.objects.filter(id__in=year_level_fees_ids)

        base_total = sum(fee.amount for fee in year_level_fees) if year_level_fees else Decimal("0.00")

        
        try:
            discount = FeeDiscount.objects.get(student=student, is_allowed=True)
        except FeeDiscount.DoesNotExist:
            discount = None

        total_discount = Decimal("0.00")
        if discount:
            for fee in year_level_fees:
                fee_type = fee.fee_type.name.lower()
                if "admission fee" in fee_type:
                    total_discount += discount.admission_fee_discount or Decimal("0.00")
                if "tuition fee" in fee_type:
                    total_discount += discount.tuition_fee_discount or Decimal("0.00")

        discounted_total = max(base_total - total_discount, Decimal("0.00"))

 
        today = date.today()
        late_fee = Decimal("0.00")
        if any("tuition fee" in fee.fee_type.name.lower() for fee in year_level_fees) and today.day > 15:
            late_fee = Decimal("25.00")

    
        total_with_late_fee = discounted_total + late_fee

   
        due_amount = max(total_with_late_fee - paid_amount, Decimal("0.00"))

        data['total_amount'] = discounted_total  
        data['late_fee'] = late_fee
        data['due_amount'] = due_amount
        data['paid_amount'] = paid_amount

     
        razorpay_payment_id = self.initial_data.get('razorpay_payment_id')
        razorpay_signature_id = self.initial_data.get('razorpay_signature_id')
        
        print(f"DEBUG: Payment Mode: {payment_mode}")
        print(f"DEBUG: Razorpay Payment ID: {razorpay_payment_id}")
        print(f"DEBUG: Razorpay Signature ID: {razorpay_signature_id}")
        print(f"DEBUG: Paid Amount: {paid_amount}")
        print(f"DEBUG: Base Amount: {discounted_total}")
        print(f"DEBUG: Late Fee: {late_fee}")
        print(f"DEBUG: Total with Late Fee: {total_with_late_fee}")

        if payment_mode == 'online':
            if razorpay_payment_id and razorpay_signature_id:
          
                if paid_amount >= total_with_late_fee:
                    data['payment_status'] = 'Paid'
                    print("DEBUG: Online Payment - STATUS: Paid (Full payment with late fee verified)")
                elif paid_amount > 0:
                    data['payment_status'] = 'Partially Paid'
                    print("DEBUG: Online Payment - STATUS: Partially Paid (Partial payment with late fee)")
                else:
                    data['payment_status'] = 'Unpaid'
                    print("DEBUG: Online Payment - STATUS: Unpaid (No payment)")
            else:
             
                data['payment_status'] = 'Unpaid'
                print("DEBUG: Online Payment - STATUS: Unpaid (Awaiting verification)")
        else:
        
            if due_amount == 0 and paid_amount > 0:
                data['payment_status'] = 'Paid'
                print("DEBUG: Cash Payment - STATUS: Paid (Full payment with late fee)")
            elif paid_amount > 0:
                data['payment_status'] = 'Partially Paid'
                print("DEBUG: Cash Payment - STATUS: Partially Paid (Partial payment with late fee)")
            else:
                data['payment_status'] = 'Unpaid'
                print("DEBUG: Cash Payment - STATUS: Unpaid")

 
        if 'razorpay_order_id' in self.initial_data:
            data['razorpay_order_id'] = self.initial_data.get('razorpay_order_id')
        if 'razorpay_payment_id' in self.initial_data:
            data['razorpay_payment_id'] = self.initial_data.get('razorpay_payment_id')
        if 'razorpay_signature_id' in self.initial_data:
            data['razorpay_signature_id'] = self.initial_data.get('razorpay_signature_id')

        return data

    def create(self, validated_data):
        year_level_fees = validated_data.pop('year_level_fees', [])
        
     
        payment_mode = validated_data.get('payment_mode', '').lower()
        razorpay_payment_id = validated_data.get('razorpay_payment_id')
        paid_amount = validated_data.get('paid_amount', Decimal('0.00'))
        base_amount = validated_data.get('total_amount', Decimal('0.00'))
        late_fee = validated_data.get('late_fee', Decimal('0.00'))
        
        total_with_late_fee = base_amount + late_fee
        
        print(f"CREATE DEBUG: Payment Mode: {payment_mode}")
        print(f"CREATE DEBUG: Razorpay Payment ID: {razorpay_payment_id}")
        print(f"CREATE DEBUG: Paid Amount: {paid_amount}")
        print(f"CREATE DEBUG: Base Amount: {base_amount}")
        print(f"CREATE DEBUG: Late Fee: {late_fee}")
        print(f"CREATE DEBUG: Total with Late Fee: {total_with_late_fee}")
        print(f"CREATE DEBUG: Initial Status: {validated_data.get('payment_status')}")


        if payment_mode == 'online' and razorpay_payment_id:
            if paid_amount >= total_with_late_fee:
                validated_data['payment_status'] = 'Paid'
                print("CREATE DEBUG: Setting status to Paid (Online payment with late fee)")
            elif paid_amount > 0:
                validated_data['payment_status'] = 'Partially Paid'
                print("CREATE DEBUG: Setting status to Partially Paid (Online partial payment with late fee)")
            else:
                validated_data['payment_status'] = 'Unpaid'
                print("CREATE DEBUG: Setting status to Unpaid (Online payment failed)")

        fee_record = FeeRecord.objects.create(**validated_data)
        fee_record.year_level_fees.set(year_level_fees)


        if not fee_record.receipt_number:
            fee_record.receipt_number = self.generate_unique_receipt_number()
            fee_record.save()

        print(f"CREATE DEBUG: Final Status Saved: {fee_record.payment_status}")
        return fee_record

    def generate_unique_receipt_number(self):
        today = datetime.now().strftime('%Y%m%d')
        last_receipt = FeeRecord.objects.filter(receipt_number__startswith=f'REC-{today}') \
                                        .aggregate(Max('receipt_number'))
        if last_receipt['receipt_number__max']:
            last_number = int(last_receipt['receipt_number__max'].split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        return f'REC-{today}-{new_number:05d}'
  
class RazorpayConfirmPaymentSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature_id = serializers.CharField()


# ********************OfficeStaffSerializer profile*******************************
# class OfficeStaffSerializer(serializers.ModelSerializer):
#     first_name = serializers.CharField(max_length=100, write_only=True)
#     middle_name = serializers.CharField(max_length=100, write_only=True, required=False, allow_blank=True)
#     last_name = serializers.CharField(max_length=100, write_only=True)
#     password = serializers.CharField(max_length=100, write_only=True, required=False)
#     email = serializers.EmailField(write_only=True)
#     user_profile = serializers.ImageField(required=False, allow_null=True, write_only=True)

#     student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), many=True, required=False)
#     teacher = serializers.PrimaryKeyRelatedField(queryset=Teacher.objects.all(), many=True, required=False)
#     admissions = serializers.PrimaryKeyRelatedField(queryset=Admission.objects.all(), many=True, required=False)

#     class Meta:
#         model = OfficeStaff
#         exclude = ["user"]

#     def create(self, validated_data):
#         user_data = {
#             "first_name": validated_data.pop("first_name"),
#             "middle_name": validated_data.pop("middle_name", ""),
#             "last_name": validated_data.pop("last_name"),
#             "password": validated_data.pop("password", None),
#             "email": validated_data.pop("email"),
#             "user_profile": validated_data.pop("user_profile", None),
#         }

#         student_data = validated_data.pop("student", [])
#         teacher_data = validated_data.pop("teacher", [])
#         admissions_data = validated_data.pop("admissions", [])

#         try:
#             role, _ = Role.objects.get_or_create(name="office_staff")
#         except MultipleObjectsReturned:
#             raise serializers.ValidationError("Multiple roles named 'office_staff' found.")

#         user = User.objects.filter(email=user_data["email"]).first()

#         if user:
#             if not user.role.filter(name="office_staff").exists():
#                 user.role.add(role)
#                 user.save()
#             else:
#                 raise serializers.ValidationError("User with this email already exists and is an office staff.")
#         else:
#             user = User.objects.create_user(**user_data)
#             user.role.add(role)
#             user.save()

#         office_staff = OfficeStaff.objects.create(user=user, **validated_data)
#         office_staff.student.set(student_data)
#         office_staff.teacher.set(teacher_data)
#         office_staff.admissions.set(admissions_data)
#         return office_staff

#     def update(self, instance, validated_data):
#         user = instance.user

#         user.first_name = validated_data.pop("first_name", user.first_name)
#         user.middle_name = validated_data.pop("middle_name", user.middle_name)
#         user.last_name = validated_data.pop("last_name", user.last_name)
#         user.email = validated_data.pop("email", user.email)
#         if "password" in validated_data and validated_data["password"]:
#             user.set_password(validated_data["password"])
#         if "user_profile" in validated_data:
#             user.user_profile = validated_data["user_profile"]

#         user.save()

#         instance.phone_no = validated_data.get("phone_no", instance.phone_no)
#         instance.gender = validated_data.get("gender", instance.gender)
#         instance.department = validated_data.get("department", instance.department)
#         instance.save()

#         if "student" in validated_data:
#             instance.student.set(validated_data["student"])
#         if "teacher" in validated_data:
#             instance.teacher.set(validated_data["teacher"])
#         if "admissions" in validated_data:
#             instance.admissions.set(validated_data["admissions"])

#         return instance

#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         representation.update({
#             "first_name": instance.user.first_name,
#             "middle_name": instance.user.middle_name,
#             "last_name": instance.user.last_name,
#             "email": instance.user.email,
#             "user_profile": instance.user.user_profile.url if instance.user.user_profile else None,
#         })

#         # Remove relational fields from the output
#         representation.pop("student", None)
#         representation.pop("teacher", None)
#         representation.pop("admissions", None)

#         return representation


class OfficeStaffSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(max_length=100, write_only=True)
    middle_name = serializers.CharField(max_length=100, write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=100, write_only=True)
    password = serializers.CharField(max_length=100, write_only=True, required=False)
    email = serializers.EmailField(write_only=True)
    user_profile = serializers.ImageField(required=False, allow_null=True, write_only=True)

    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), many=True, required=False)
    teacher = serializers.PrimaryKeyRelatedField(queryset=Teacher.objects.all(), many=True, required=False)
    admissions = serializers.PrimaryKeyRelatedField(queryset=Admission.objects.all(), many=True, required=False)
    phone_no = serializers.CharField(required=False,allow_blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?\d{10,15}$',
                message="Enter a valid phone number (10-15 digits, optional + at start).")])
    adhaar_no = serializers.CharField(required=False,allow_blank=True,
        validators=[
            RegexValidator(
                regex=r'^\d{12}$',
                message="Enter a valid 12-digit Aadhaar number.")])

    pan_no = serializers.CharField(required=False,allow_blank=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z]{5}[0-9]{4}[A-Z]$',
                message="Enter a valid PAN number (e.g., ABCDE1234F).")])
    gender = serializers.ChoiceField(
        choices=[('Male','Male'),('Female','Female'),('Other','Other')],
        required=False,
        error_messages={"invalid_choice": "Gender must be Male, Female, or Other."}
    )
    
    class Meta:
        model = OfficeStaff
        exclude = ["user"]

    def create(self, validated_data):
        user_data = {
            "first_name": validated_data.pop("first_name"),
            "middle_name": validated_data.pop("middle_name", ""),
            "last_name": validated_data.pop("last_name"),
            "password": validated_data.pop("password", None),
            "email": validated_data.pop("email"),
            "user_profile": validated_data.pop("user_profile", None),
        }

        student_data = validated_data.pop("student", [])
        teacher_data = validated_data.pop("teacher", [])
        admissions_data = validated_data.pop("admissions", [])

        try:
            role, _ = Role.objects.get_or_create(name="office_staff")
        except MultipleObjectsReturned:
            raise serializers.ValidationError("Multiple roles named 'office_staff' found.")

        user = User.objects.filter(email=user_data["email"]).first()

        if user:
            if not user.role.filter(name="office_staff").exists():
                user.role.add(role)
                user.save()
            else:
                raise serializers.ValidationError("User with this email already exists and is an office staff.")
        else:
            user = User.objects.create_user(**user_data)
            user.role.add(role)
            user.save()

        office_staff = OfficeStaff.objects.create(user=user, **validated_data)
        office_staff.student.set(student_data)
        office_staff.teacher.set(teacher_data)
        office_staff.admissions.set(admissions_data)
        return office_staff

    def update(self, instance, validated_data):
        user = instance.user

        user.first_name = validated_data.pop("first_name", user.first_name)
        user.middle_name = validated_data.pop("middle_name", user.middle_name)
        user.last_name = validated_data.pop("last_name", user.last_name)
        user.email = validated_data.pop("email", user.email)
        if "password" in validated_data and validated_data["password"]:
            user.set_password(validated_data["password"])
        if "user_profile" in validated_data:
            user.user_profile = validated_data["user_profile"]

        user.save()

        instance.phone_no = validated_data.get("phone_no", instance.phone_no)
        instance.gender = validated_data.get("gender", instance.gender)
        instance.department = validated_data.get("department", instance.department)
        instance.adhaar_no = validated_data.get("adhaar_no", instance.adhaar_no)  #  added as of 09Sep25
        instance.pan_no = validated_data.get("pan_no", instance.pan_no)          #  added as of 09Sep25
        instance.save()

        if "student" in validated_data:
            instance.student.set(validated_data["student"])
        if "teacher" in validated_data:
            instance.teacher.set(validated_data["teacher"])
        if "admissions" in validated_data:
            instance.admissions.set(validated_data["admissions"])

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.update({
            "first_name": instance.user.first_name,
            "middle_name": instance.user.middle_name,
            "last_name": instance.user.last_name,
            "email": instance.user.email,
            "user_profile": instance.user.user_profile.url if instance.user.user_profile else None,
            "adhaar_no": instance.adhaar_no,   #  added as of 09Sep25
            "pan_no": instance.pan_no,         #  added as of 09Sep25
        })

        # Remove relational fields from the output
        representation.pop("student", None)
        representation.pop("teacher", None)
        representation.pop("admissions", None)

        return representation




    
    
    
    # ******************DocumentTypeSerializer*************************
    

# import json

class DocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = "__all__"


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ['id', 'file']



# class DocumentSerializer(serializers.ModelSerializer):
#     files = FileSerializer(many=True, read_only=True)

#     uploaded_files = serializers.ListField(
#         child=serializers.FileField(),
#         write_only=True,
#         required=True,
#         allow_empty=False
#     )

#     # Accepts list of IDs at POST/PUT time
#     document_types = serializers.PrimaryKeyRelatedField(
#         queryset=DocumentType.objects.all(),
#         many=True,
#         required=True,
#         allow_empty=False
#     )

#     identities = serializers.ListField(
#         child=serializers.CharField(),
#         write_only=True
#     )

#     identities_read = serializers.SerializerMethodField(read_only=True)

#     class Meta:
#         model = Document
#         fields = [
#             'id', 'document_types', 'identities', 'identities_read', 'files', 'uploaded_files',
#             'student', 'teacher', 'guardian', 'office_staff', 'uploaded_at'
#         ]

#     def get_identities_read(self, obj):
#         import json
#         try:
#             return json.loads(obj.identities) if obj.identities else []
#         except:
#             return []

#     def to_representation(self, instance):
#         """Customize the output to show document type names instead of just IDs."""
#         representation = super().to_representation(instance)
#         document_types = instance.document_types.all()
#         representation['document_types'] = [
#             {"id": dt.id, "name": dt.name} for dt in document_types
#         ]
#         return representation

#     def create(self, validated_data):
#         import json

#         uploaded_files = validated_data.pop('uploaded_files')
#         document_types = validated_data.pop('document_types')
#         identities_list = validated_data.pop('identities')

#         if len(document_types) != len(identities_list):
#             raise serializers.ValidationError("Number of document_types and identities must match.")

#         document = Document.objects.create(**validated_data)
#         document.document_types.set(document_types)
#         document.identities = json.dumps(identities_list)
#         document.save()

#         for uploaded_file in uploaded_files:
#             File.objects.create(file=uploaded_file, document=document)

#         return document



# from rest_framework import serializers
# from .models import Document, DocumentType

# class DocumentSerializer(serializers.ModelSerializer):
#     # Make document_types write-only to prevent it from being included in validated_data
#     document_types = serializers.PrimaryKeyRelatedField(
#         many=True,
#         queryset=DocumentType.objects.all(),
#         write_only=True
#     )
    
#     # Add read-only field for the response
#     document_types_read = serializers.PrimaryKeyRelatedField(
#         many=True,
#         source='document_types',
#         read_only=True
#     )
    
#     class Meta:
#         model = Document
#         fields = '__all__'
#         extra_kwargs = {
#             'student': {'required': False, 'allow_null': True},
#             'teacher': {'required': False, 'allow_null': True},
#             'guardian': {'required': False, 'allow_null': True},
#             'office_staff': {'required': False, 'allow_null': True},
#         }

#     def create(self, validated_data):
#         # Remove document_types from validated_data before creation
#         document_types = validated_data.pop('document_types', [])
        
#         # Create the document instance
#         instance = super().create(validated_data)
        
#         # Set the many-to-many relationship after creation
#         if document_types:
#             instance.document_types.set(document_types)
        
#         return instance

#     def update(self, instance, validated_data):
#         # Handle document_types separately for updates too
#         document_types = validated_data.pop('document_types', None)
        
#         instance = super().update(instance, validated_data)
        
#         if document_types is not None:
#             instance.document_types.set(document_types)
        
#         return instance

from rest_framework import serializers
from .models import Document, DocumentType


class DocumentSerializer(serializers.ModelSerializer):
    document_types = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=DocumentType.objects.all(),
        write_only=True
    )
    
    document_types_read = serializers.PrimaryKeyRelatedField(
        many=True,
        source='document_types',
        read_only=True
    )
    
    files = FileSerializer(many=True, read_only=True)
    
    class Meta:
        model = Document
        fields = '__all__'
        extra_kwargs = {
            'student': {'required': False, 'allow_null': True},
            'teacher': {'required': False, 'allow_null': True},
            'guardian': {'required': False, 'allow_null': True},
            'office_staff': {'required': False, 'allow_null': True},
        }

    def create(self, validated_data):
        document_types = validated_data.pop('document_types', [])
        instance = super().create(validated_data)
        
        if document_types:
            instance.document_types.set(document_types)
        
        # Handle file creation separately in the view
        return instance
    
    def to_representation(self, instance):
        """Customize the output to show document type names instead of just IDs."""
        representation = super().to_representation(instance)
        document_types = instance.document_types.all()
        
        identities_read = representation.pop("identities")
        
        # it shows the which type of document user have.
        representation['document_types_read'] = [
            {"name": dt.name} for dt in document_types
        ]
        
        student_id = representation.pop("student")
        teacher_id = representation.pop("teacher")
        office_staff_id = representation.pop("office_staff")
        guardian_id = representation.pop("guardian")

        
        rep = representation
        
        try:
            if student_id:
                student = Student.objects.get(id=student_id)
                rep["student_id"] = student.id
                rep["student_name"] = f"{student.user.first_name} {student.user.last_name}"
                studentyearlevel = StudentYearLevel.objects.get(student_id = student_id)
                rep["year_level"] = studentyearlevel.level.level_name
                rep["scholar_number"] = student.scholar_number

            if teacher_id:
                teacher = Teacher.objects.get(id = teacher_id)
                rep["teacher_id"] = teacher.id
                rep["teacher_name"] = f"{teacher.user.first_name} {teacher.user.last_name}"
                
            if guardian_id:
                guardian = Guardian.objects.get(id = guardian_id)
                rep["guardian_id"] = guardian.id
                rep["guardian_name"] = f"{guardian.user.first_name} {guardian.user.last_name}"
                
            if office_staff_id:
                office_staff = OfficeStaff.objects.get(id = office_staff_id)
                rep["office_staff_id"] = office_staff.id
                rep["office_staff_name"] = f"{office_staff.user.first_name} {office_staff.user.last_name}"
            
            
        except User.DoesNotExist:
            rep["user"] = "This user doesn't exist..!"
        
        return rep
# --------------------exam module
class ExamPaperItemSerializer(serializers.Serializer):
    subject_id = serializers.IntegerField()
    exam_date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()

MAX_SUBJECTS_PER_TIMETABLE = 10  
from collections import Counter
class ExamScheduleSerializer(serializers.Serializer):
    class_name = serializers.IntegerField()
    school_year = serializers.IntegerField()
    exam_type = serializers.IntegerField()
    papers = ExamPaperItemSerializer(many=True)

    def validate(self, data):
        subject_ids = [paper["subject_id"] for paper in data.get("papers", [])]

        # Duplicate subjects
        duplicate_subjects = [sub_id for sub_id, count in Counter(subject_ids).items() if count > 1]
        if duplicate_subjects:
            raise serializers.ValidationError({
                "papers": f"Duplicate subject(s) found in timetable: {duplicate_subjects}"
            })
        
        class_id = data["class_name"]
        exam_type_id = data["exam_type"]
        school_year_id = data["school_year"]
        papers = data.get("papers", [])

        class_obj = YearLevel.objects.get(id=class_id)
        max_per_date = 3 if class_obj.level_order >= 15 else 1

        school_year = SchoolYear.objects.get(id=school_year_id)
        term = Term.objects.filter(year=school_year).first()
        if not term:
            raise serializers.ValidationError({"term": f"No term found for school year '{school_year.year_name}'"})

        existing_papers = ExamSchedule.objects.filter(
            class_name_id=class_id,
            exam_type_id=exam_type_id,
            term_id=term.id
        )

        # check total subjects per timetable 
        total_subjects_after_add = existing_papers.count() + len(papers)
        if total_subjects_after_add > MAX_SUBJECTS_PER_TIMETABLE:
            raise serializers.ValidationError({
                "papers": f"Cannot add {len(papers)} subjects. This timetable already has {existing_papers.count()} subjects. Max allowed per timetable is {MAX_SUBJECTS_PER_TIMETABLE}."
            })


        date_counter = Counter([str(p.exam_date) for p in existing_papers])
        for p in papers:
            date_counter[str(p["exam_date"])] += 1

        # check if any date exceeds max allowed
        over_limit_dates = [d for d, cnt in date_counter.items() if cnt > max_per_date]
        if over_limit_dates:
            raise serializers.ValidationError({
                "papers": f"Too many papers on date(s): {over_limit_dates} (max {max_per_date})"
            })

        # only one date can have max papers, others must have 1 each
        # max_count_dates = [d for d, cnt in date_counter.items() if cnt == max_per_date]
        # if len(max_count_dates) > 1:
        #     raise serializers.ValidationError({
        #         # "papers": f"Sirf ek date par maximum {max_per_date} papers ho sakte hain, baaki dates me 1 paper hi ho sakta hai."
        #         "papers": f"For {class_obj.level_name}, only one day is allowed to have {max_per_date} exams. Every other day must have only one exam."
        #     })

        # for d, cnt in date_counter.items():
        #     if d not in max_count_dates and cnt != 1:
        #         raise serializers.ValidationError({
        #             # "papers": f"{class_obj.level_name} me {d} par 1 paper hona chahiye."
        #             "papers": f"{class_obj.level_name} can have only one subject scheduled on {d}."
        #         })

        # Flexible multiple dates validation
        date_counter = Counter([str(p.exam_date) for p in existing_papers])
        for p in papers:
            date_counter[str(p["exam_date"])] += 1

        if class_obj.level_order < 15:  # Pre Nursery–Class 10
            for date, count in date_counter.items():
                if count != 1:
                    raise serializers.ValidationError({
                        "papers": f"{class_obj.level_name} can have only one subject scheduled on {date}."
                    })
        else:  # Class 11 & 12
            max_per_date = 3
            over_limit_dates = [d for d, cnt in date_counter.items() if cnt > max_per_date]
            if over_limit_dates:
                raise serializers.ValidationError({
                    "papers": f"Too many papers on date(s): {over_limit_dates} (max {max_per_date})"
                })

        # Duplicate subjects per date
        subject_dates = [(paper['subject_id'], str(paper['exam_date'])) for paper in papers]
        if len(subject_dates) != len(set(subject_dates)):
            raise serializers.ValidationError({
                "papers": "Duplicate subjects scheduled on the same date are not allowed."
            })


        return data


    def validate_paper(self, paper):
        subject_id = paper.get("subject_id")

        # Subject existence
        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            raise serializers.ValidationError({
                "subject": f"Subject with ID {subject_id} does not exist."
            })
        
        exam_date = paper["exam_date"]
        if isinstance(exam_date, str):
            exam_date = datetime.strptime(exam_date, "%Y-%m-%d").date()

        exam_date = paper["exam_date"]

        # Past date check
        if exam_date < date.today():
            raise serializers.ValidationError({
                "exam_date": f"Exam date for subject '{subject.subject_name}' cannot be in the past."
            })

        # Future date limit
        max_future_date = date.today().replace(year=date.today().year + 1)
        if exam_date > max_future_date:
            raise serializers.ValidationError({
                "exam_date": f"Exam date for subject '{subject.subject_name}' cannot be more than 1 year in the future."
            })

        # Sunday check
        if exam_date.weekday() == 6:
            raise serializers.ValidationError({
                "exam_date": f"Exams cannot be scheduled on Sunday: {exam_date}"
            })

        start_time = paper["start_time"]
        end_time = paper["end_time"]

        # Start < End
        if start_time >= end_time:
            raise serializers.ValidationError({
                "time": f"Exam for '{subject.subject_name}' must have start time before end time."
            })



        # Duration check (≤ 3 hours)
        start_dt = datetime.combine(datetime.today(), paper["start_time"])
        end_dt = datetime.combine(datetime.today(), paper["end_time"])
        duration = end_dt - start_dt

        if duration > timedelta(hours=3):
            raise serializers.ValidationError({
                "time": f"Exam duration for subject '{subject.subject_name}' cannot exceed 3 hours."
            })

        # Allowed time range (8:00 AM to 5:00 PM)
        def format_time_12hr(t: time):
            return t.strftime("%I:%M %p")  # 08:00 AM, 05:00 PM

        allowed_start = time(8, 0)  # 08:00 AM
        allowed_end = time(17, 0)   # 05:00 PM

        if not (allowed_start <= paper["start_time"] <= allowed_end):
            raise serializers.ValidationError({
                "start_time": f"Exam for '{subject.subject_name}' must start between {format_time_12hr(allowed_start)} and {format_time_12hr(allowed_end)}."
            })

        if not (allowed_start <= paper["end_time"] <= allowed_end):
            raise serializers.ValidationError({
                "end_time": f"Exam for '{subject.subject_name}' must end between {format_time_12hr(allowed_start)} and {format_time_12hr(allowed_end)}."
            })
      
        class_id = self.initial_data.get("class_name")
        exam_type_id = self.initial_data.get("exam_type")
        school_year_id = self.initial_data.get("school_year")

        if not class_id:
            raise serializers.ValidationError({"class_name": "Class is required for exam scheduling."})

        # Get class object
        class_obj = YearLevel.objects.get(id=class_id)

        # Determine max exams per date based on class
        if class_obj.level_order >= 15:  # Class 11 & 12
            max_allowed = 3
        else:  # Class ≤ 10
            max_allowed = 1

        # Existing exams for this class, date, type, year
        existing_exams_count = ExamSchedule.objects.filter(
            class_name_id=class_id,
            exam_date=exam_date,
            exam_type_id=exam_type_id,
            term__year_id=school_year_id
        ).count()

        if existing_exams_count >= max_allowed:
            raise serializers.ValidationError({
                "exam_date": f"{class_obj.level_name} can have maximum {max_allowed} exam(s) on {exam_date}."
            })


    def create(self, validated_data):
        class_id = validated_data["class_name"]
        year_id = validated_data["school_year"]
        exam_type_id = validated_data["exam_type"]
        # papers_data = validated_data["papers"]
        papers_data = validated_data.get("papers", [])


        try:
            school_year = SchoolYear.objects.get(id=year_id)
        except SchoolYear.DoesNotExist:
            raise serializers.ValidationError({"school_year": f"School year with ID {year_id} not found"})

        term = Term.objects.filter(year=school_year).first()
        if not term:
            raise serializers.ValidationError({"term": f"No term found for school year '{school_year.year_name}'"})

        created_schedules = []
        for paper in papers_data:
            self.validate_paper(paper)
            subject_id = paper["subject_id"]

            existing_schedule = ExamSchedule.objects.filter(
                class_name_id=class_id,
                exam_type_id=exam_type_id,
                subject_id=subject_id,
                term_id=term.id
            ).first()

            if existing_schedule:
                subject = Subject.objects.get(id=subject_id)
                level = YearLevel.objects.get(id=class_id)
                exam_type = ExamType.objects.get(id=exam_type_id)

                raise serializers.ValidationError(
                    f"Subject '{subject.subject_name}' is already scheduled for class '{level.level_name}', "
                    f"year '{school_year.year_name}', and exam type '{exam_type.name}'."
                )

            schedule = ExamSchedule.objects.create(
                exam_date=paper["exam_date"],
                start_time=paper["start_time"],
                end_time=paper["end_time"],
                exam_type_id=exam_type_id,
                class_name_id=class_id,
                term_id=term.id,
                subject_id=subject_id
            )

            created_schedules.append(schedule)

        return created_schedules


    def update(self, instance, validated_data):
        class_id = validated_data["class_name"]
        year_id = validated_data["school_year"]
        exam_type_id = validated_data["exam_type"]
        papers_data = validated_data["papers"]

        level = YearLevel.objects.get(id=class_id)
        year = SchoolYear.objects.get(id=year_id)
        exam_type = ExamType.objects.get(id=exam_type_id)

        result = []

        def safe_serialize(value):
            if isinstance(value, (date, time, datetime)):
                return value.isoformat()
            return str(value)

        for paper in papers_data:
            self.validate_paper(paper)
            subject_id = paper.get("subject_id")

            try:
                schedule = ExamSchedule.objects.get(
                    subject_id=subject_id,
                    exam_type_id=exam_type_id,
                    class_name_id=class_id,
                )
            except ExamSchedule.DoesNotExist:
                raise serializers.ValidationError(f"Schedule not found for subject ID {subject_id}")

            except ExamSchedule.MultipleObjectsReturned:
                subject = Subject.objects.filter(id=subject_id).first()
                subject_name = subject.subject_name if subject else f"ID {subject_id}"

                raise serializers.ValidationError(
                    f"Duplicate entry found: Subject '{subject_name}' already has a schedule for "
                    f"class '{level.level_name}', school year '{year.year_name}', and exam type '{exam_type.name}'."
                )


            schedule.exam_date = paper["exam_date"]
            schedule.start_time = paper["start_time"]
            schedule.end_time = paper["end_time"]
            schedule.day = paper["exam_date"].strftime('%A')
            schedule.save()

            subject = Subject.objects.get(id=subject_id)

            result.append({
                "subject_name": subject.subject_name,
                "exam_date": safe_serialize(schedule.exam_date),
                "start_time": safe_serialize(schedule.start_time),
                "end_time": safe_serialize(schedule.end_time),
                "day": schedule.day
            })

        return {
            "class": level.level_name,
            "school_year": year.year_name,
            "exam_type": exam_type.name,
            "papers": result
        }



# class ExamScheduleSerializer(serializers.ModelSerializer):
#     # Read-only fields for display
#     class_name = serializers.CharField(source="class_name.level_name", read_only=True)
#     school_year = serializers.CharField(source="term.year.year_name", read_only=True)
#     exam_type = serializers.CharField(source="exam_type.name", read_only=True)
#     subject = serializers.CharField(source="subject.subject_name", read_only=True)

#     # Write-only IDs for create/update
#     class_name_id = serializers.IntegerField(write_only=True)
#     school_year_id = serializers.IntegerField(write_only=True)
#     exam_type_id = serializers.IntegerField(write_only=True)
#     subject_id = serializers.IntegerField(write_only=True)

#     class Meta:
#         model = ExamSchedule
#         fields = [
#             "id",
#             # read-only
#             "class_name",
#             "school_year",
#             "exam_type",
#             "subject",
#             # write-only IDs
#             "class_name_id",
#             "school_year_id",
#             "exam_type_id",
#             "subject_id",
#             # normal fields (jo model me exist karte hain)
#             "exam_date",
#             "start_time",
#             "end_time",
#         ]

#     def create(self, validated_data):
#         class_name = YearLevel.objects.get(id=validated_data.pop("class_name_id"))
#         term = Term.objects.get(id=validated_data.pop("school_year_id"))
#         exam_type = ExamType.objects.get(id=validated_data.pop("exam_type_id"))
#         subject = Subject.objects.get(id=validated_data.pop("subject_id"))

#         return ExamSchedule.objects.create(
#             class_name=class_name,
#             term=term,
#             exam_type=exam_type,
#             subject=subject,
#             **validated_data
#         )

#     def update(self, instance, validated_data):
#         if "class_name_id" in validated_data:
#             instance.class_name = YearLevel.objects.get(
#                 id=validated_data.pop("class_name_id")
#             )
#         if "school_year_id" in validated_data:
#             instance.term = Term.objects.get(id=validated_data.pop("school_year_id"))
#         if "exam_type_id" in validated_data:
#             instance.exam_type = ExamType.objects.get(
#                 id=validated_data.pop("exam_type_id")
#             )
#         if "subject_id" in validated_data:
#             instance.subject = Subject.objects.get(
#                 id=validated_data.pop("subject_id")
#             )

#         for attr, value in validated_data.items():
#             setattr(instance, attr, value)

#         instance.save()
#         return instance







class ExamTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamType
        fields = "__all__"


class ExamPaperSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    year_level_name = serializers.CharField(source='year_level.level_name', read_only=True)
    exam_name = serializers.CharField(source='exam_type.name', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    year = serializers.CharField(source='term.year.year_name', read_only=True)
    uploaded_file_url = serializers.SerializerMethodField()

    class Meta:
        model = ExamPaper
        fields = [
            'id', 'subject_name', 'year_level_name', 'exam_name', 'teacher_name',
            'total_marks', 'paper_code', 'uploaded_file', 'year',
            'exam_type', 'term', 'subject', 'year_level', 'teacher','uploaded_file_url'
        ]
        extra_kwargs = {
            'exam_type': {'write_only': True},
            'term': {'write_only': True},
            'subject': {'write_only': True},
            'year_level': {'write_only': True},
            'teacher': {'write_only': True}
        }

    def get_teacher_name(self, obj):
        if obj.teacher and obj.teacher.user:
            return obj.teacher.user.get_full_name()
        return None


    # def get_uploaded_file_url(self, obj):
    #     import os
    #     from django.conf import settings

    #     if obj.uploaded_file:
    #         file_path = os.path.join(settings.MEDIA_ROOT, obj.uploaded_file.name)
    #         if os.path.exists(file_path):
    #             return obj.uploaded_file.url
    #         else:
    #             return "File has been deleted or not found"
    #     return None
    def get_uploaded_file_url(self, obj):
        # Check if file exists
        if obj.uploaded_file and obj.uploaded_file.storage.exists(obj.uploaded_file.name):
            request = self.context.get('request')
            return request.build_absolute_uri(obj.uploaded_file.url)
        return None  # ya "File has been deleted or not found"


    def validate_uploaded_file(self, value):
        # 1. File size check like 5 MB
        MAX_FILE_SIZE = 5 * 1024 * 1024  
        file_size = getattr(value, 'size', 0)
        if file_size > MAX_FILE_SIZE:
            raise ValidationError(f"File size should not exceed {MAX_FILE_SIZE / (1024*1024)} MB.")

        # 2. Extension check
        ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif']
        file_name = getattr(value, 'name', None)
        ext = os.path.splitext(file_name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError(f"Files with extension '{ext}' are not allowed.")

        # 3. MIME type check (if available)
        ALLOWED_MIME_TYPES = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'image/jpeg',
            'image/png',
            'image/gif'
        ]
        file_type = getattr(value, 'content_type', None) or getattr(getattr(value, 'file', None), 'content_type', None)
        if file_type and file_type not in ALLOWED_MIME_TYPES:
            raise ValidationError(f"Files of type '{file_type}' are not allowed.")
        return value
        
    def validate_total_marks(self, value):
        if value < 0:
            raise serializers.ValidationError("Total marks cannot be negative.")

        exam_type_id = self.initial_data.get("exam_type")
        if not exam_type_id:
            return value

        try:
            exam_type = ExamType.objects.get(id=exam_type_id)
        except ExamType.DoesNotExist:
            return value

        name = exam_type.name.upper()
        if name in ["SA1", "SA2"] and value > 100:
            raise serializers.ValidationError("Total marks for SA1/SA2 cannot exceed 100.")
        elif name in ["FA1", "FA2", "FA3"] and value > 20:
            raise serializers.ValidationError("Total marks for FA1/FA2/FA3 cannot exceed 20.")
        return value


    def create(self, validated_data):
        subject = validated_data["subject"]
        exam_type = validated_data["exam_type"]
        term = validated_data["term"]
        year_level = validated_data["year_level"]
        paper_code = validated_data["paper_code"]

        if ExamPaper.objects.filter(
            subject=subject,
            exam_type=exam_type,
            term=term,
            year_level=year_level
        ).exists():
            raise serializers.ValidationError(
                f"Exam paper already exists for subject '{subject.subject_name}', "
                f"class '{year_level.level_name}', year '{term.year.year_name}', and exam '{exam_type.name}'."
            )
        
        if ExamPaper.objects.filter(paper_code=paper_code).exists():
            raise serializers.ValidationError({"paper_code": ["exam paper with this paper code already exists."]})

        return super().create(validated_data)



    def update(self, instance, validated_data):
        subject = validated_data.get("subject", instance.subject)
        teacher = validated_data.get("teacher", instance.teacher)
        paper_code = validated_data.get("paper_code", instance.paper_code)
        total_marks = validated_data.get("total_marks", instance.total_marks)

        if ExamPaper.objects.exclude(id=instance.id).filter(
            subject=subject,
            exam_type=instance.exam_type,
            term=instance.term,
            year_level=instance.year_level
        ).exists():
            raise serializers.ValidationError(
                f"Exam paper already exists for this subject, class, year, and exam type."
            )

        if ExamPaper.objects.exclude(id=instance.id).filter(paper_code=paper_code).exists():
            raise serializers.ValidationError({"paper_code": ["exam paper with this paper code already exists."]})


        instance.subject = subject
        instance.teacher = teacher
        instance.paper_code = paper_code
        instance.total_marks = total_marks

        instance.save()
        return instance


class StudentMarksSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.user.first_name', read_only=True)
    school_year = serializers.CharField(source='term.year.year_name', read_only=True)
    year_level = serializers.CharField(source='student.year_level.level_name', read_only=True)
    subject = serializers.CharField(source='subject.subject_name', read_only=True)
    exam_type = serializers.CharField(source='exam_type.name', read_only=True)
    student_name = serializers.CharField(source='student.user.first_name', read_only=True)
    marks = serializers.DecimalField(source='marks_obtained', max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = StudentMarks
        fields = ['id','teacher_name','school_year','year_level','subject','exam_type','student_name','marks']






"""---------------------------------------------RESULT---------------------------------------------------------------------"""

"""----------------------------------------ReportCardDocument-------------------------------------------------"""
class ReportCardDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportCardDocument
        fields = '__all__'

"""----------------------------------------SubjectScore----------------------------------------------------"""
class StudentMarksMiniSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.first_name", read_only=True)
    subject_name = serializers.CharField(source="subject.subject_name")
    exam_type = serializers.CharField(source="exam_type.name")
    marks_obtained = serializers.DecimalField(decimal_places=2,max_digits=5,required=False,allow_null=True,coerce_to_string=False)

    class Meta:
        model = StudentMarks
        fields = ["student_name","exam_type", "subject_name", "marks_obtained"]
    
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        marks = rep.get("marks_obtained")
        try:
            rep["marks_obtained"] = str(marks) if marks is not None else "0.00"
        except:
            rep["marks_obtained"] = "0.00"
        return rep

    
class SubjectScoreSerializer(serializers.ModelSerializer):
    marks_obtained = StudentMarksMiniSerializer()
    # print("marks_obtained", marks_obtained )
    class Meta:
        model = SubjectScore
        fields = ["marks_obtained"]

"""----------------------------------------NonScholasticGradeTermWise-------------------------------------------------"""

class PersonalSocialQualitySerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonalSocialQuality
        fields = "__all__"

class NonScholasticGradeTermWiseSerializer(serializers.ModelSerializer):
    ALLOWED_GRADES = ["A++", "A+", "A", "B", "C", "D"]

    def validate_non_scholastic_subject(self, subject):
        
        expected_department = "Non-scholastic"  # change if needed
        
        if not subject.department or subject.department.department_name != expected_department:
            raise serializers.ValidationError(
                f"Subject must belong to the '{expected_department}' department."
            )
        return subject

    def validate_grade(self, value):
        if value not in self.ALLOWED_GRADES:
            raise serializers.ValidationError("Grade must be one of: A++, A+, A, B, C, D.")
        return value
    
    class Meta:
        model = NonScholasticGradeTermWise
        fields = ['id', 'report_card', 'non_scholastic_subject', 'term', 'grade']

"""----------------------------------------PersonalSocialQualityTermWise-------------------------------------------------"""
      
class PersonalSocialGradeSerializer(serializers.ModelSerializer):

    ALLOWED_GRADES = ["A++", "A+", "A", "B", "C", "D"]

    def validate_grade(self, value):
        if value not in self.ALLOWED_GRADES:
            raise serializers.ValidationError("Grade must be one of: A++, A+, A, B, C, D.")
        return value

    class Meta:
        model = PersonalSocialQualityTermWise
        fields = ['id', 'report_card', 'personal_quality', 'term', 'grade']

"""----------------------------------------ReportCard-------------------------------------------------"""
    
class ReportCardSerializer(serializers.ModelSerializer):
    PersonalSocialQualityTermWise = PersonalSocialGradeSerializer(many=True, read_only=True)
    subjects = SubjectScoreSerializer(many=True,read_only=True, source='subject_scores')
    
    class Meta:
        model = ReportCard
        fields = ["id","student_level",
            "rank","percentage","grade",
            "division", "attendance","PersonalSocialQualityTermWise","subjects", "teacher_remark", "supplementary_in", "school_reopen_date", "promoted_to_class",
        ]
        read_only_fields = ["total_marks", "max_marks", "percentage","grade","division","subjects","attendance","supplementary_in", "promoted_to_class"]

    def get_promoted_to_class(self, obj):
        if obj.promoted_to_class:
            return str(obj.promoted_to_class.level.level_name)
        return '0'


# --------------------- Expense 
class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = "__all__"

class SchoolExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    approved_by_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    school_year_name = serializers.SerializerMethodField()
    # razorpay_payment_id = serializers.CharField(read_only=True)
    # razorpay_order_id = serializers.CharField(read_only=True)
    # razorpay_signature = serializers.CharField(read_only=True)
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = SchoolExpense
        fields = [
            "id", "category", "category_name", "amount", "description", "expense_date",
            "payment_method", "attachment", "status", "created_at", "created_by",
            "created_by_name", "approved_by", "approved_by_name", "school_year", "school_year_name","attachment_url"] 
            # ,"razorpay_payment_id", "razorpay_order_id", "razorpay_signature"]
        read_only_fields = [
            "created_at", "created_by", "approved_by"
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return f"{obj.approved_by.first_name} {obj.approved_by.last_name}".strip()
        return None

    def get_school_year_name(self, obj):
        return obj.school_year.year_name if obj.school_year else None

    def get_attachment_url(self, obj):
        request = self.context.get("request")
        if obj.attachment:
            if request:
                return request.build_absolute_uri(obj.attachment.url)
            # fallback agar request nahi mila
            return obj.attachment.url

    def validate_attachment(self, value):
        if not value:
            return value

        # File size check (2 MB max)
        max_size = 2 * 1024 * 1024  # 2 MB
        if value.size > max_size:
            raise serializers.ValidationError("File size must be under 2MB.")

        # File extension check
        ext = os.path.splitext(value.name)[1].lower()
        allowed_extensions = [".jpg", ".jpeg", ".png", ".webp", ".pdf"]
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"Unsupported file type '{ext}'. Allowed types are: {', '.join(allowed_extensions)}"
            )

        return value

    def validate(self, attrs):
        if self.instance and "payment_method" in attrs:
            raise serializers.ValidationError(
                {"payment_method": "Payment method cannot be changed once created."}
            )


        if self.instance and "school_year" in attrs:
            raise serializers.ValidationError(
                {"school_year": "School year cannot be changed once created."}
            )

        category = attrs.get("category") or (self.instance.category if self.instance else None)
        school_year = attrs.get("school_year") or (self.instance.school_year if self.instance else None)
        expense_date = attrs.get("expense_date") or (self.instance.expense_date if self.instance else None)

        if category and school_year:
            if category and category.name.lower() in [
                'electricity bill', 'water bill', 'wi-fi bill',
                'renovation bill', 'rent', 'salary'
            ]:
                # monthly duplicate check
                existing = SchoolExpense.objects.filter(
                    category=category,
                    school_year=school_year,
                    expense_date__year=expense_date.year,
                    expense_date__month=expense_date.month
                )
            else:
                existing = SchoolExpense.objects.filter(
                    category=category,
                    school_year=school_year
                )

            if self.instance:
                existing = existing.exclude(id=self.instance.id)

            if existing.exists():
                raise serializers.ValidationError(
                    {"non_field_errors": "This expense record already exists for the selected category and period."}
                )

        # Salary category = auto amount
        # if category and category.name.lower() == "salary":
        #     total_salary = (
        #         EmployeeSalary.objects.filter(school_year=school_year)
        #         .aggregate(total=Sum("net_amount"))["total"] or 0
        #     )
        #     attrs["amount"] = total_salary

        if category and category.name.lower() == "salary":
            expense_date = attrs.get("expense_date") or (self.instance.expense_date if self.instance else None)

            if not expense_date:
                raise serializers.ValidationError(
                    {"expense_date": "Expense date is required for salary expenses."}
                )

            month_name = calendar.month_name[expense_date.month]  # (1 → January)

            qs = EmployeeSalary.objects.filter(
                school_year=school_year,
                month=month_name
            )

            if not qs.exists():
                raise serializers.ValidationError(
                    {"non_field_errors": f"No salary records found for {month_name} {expense_date.year} in this school year."}
                )

            total_salary = qs.aggregate(total=Sum("net_amount"))["total"] or 0
            attrs["amount"] = total_salary
            print("total_salary : ",total_salary)

        if "amount" in attrs and attrs["amount"] <= 0:
            raise serializers.ValidationError({"amount": "Amount must be a positive number."})


        # if attrs.get('expense_date') and attrs['expense_date'] > date.today():
        #     raise serializers.ValidationError({"expense_date": "Expense date cannot be in the future."})

        school_year = attrs.get("school_year") or (self.instance.school_year if self.instance else None)
        if school_year:
            today = date.today()
            if not (school_year.start_date <= today <= school_year.end_date):
                raise serializers.ValidationError(
                    {"school_year": "You can only create expenses for the current school year."}
                )

        # expense_date = attrs.get('expense_date') or (self.instance.expense_date if self.instance else None)
        # school_year = attrs.get("school_year") or (self.instance.school_year if self.instance else None)

        if expense_date:

            #Future date block
            if expense_date > date.today():
                raise serializers.ValidationError({
                    "expense_date": "Expense date cannot be in the future."
                })

            #School year block 
            if school_year:
                start_year, end_year = map(int, school_year.year_name.split('-'))
                if not (start_year <= expense_date.year <= end_year):
                    raise serializers.ValidationError({
                        "expense_date": f"Expense date must be within the selected school year ({school_year.year_name})."
                    })

            #Extremely old date block
            MIN_YEAR = 2000
            if expense_date.year < MIN_YEAR:
                raise serializers.ValidationError({
                    "expense_date": f"Expense date cannot be earlier than {MIN_YEAR}."
                })

        return attrs

    def update(self, instance, validated_data):
        # Allow update only for: category, amount, description, expense_date, attachment, status.

        allowed_fields = ["category", "amount", "description", "expense_date", "attachment", "status"]

        for field, value in validated_data.items():
            if field in allowed_fields:
                setattr(instance, field, value)

        instance.save()
        return instance


class EmployeeSerializer(serializers.ModelSerializer):
    # role = serializers.CharField(source='user.role', read_only=True)
    # role = RoleSerializer(source='user.role', read_only=True)
    role = serializers.SerializerMethodField()
    name = serializers.CharField(source="user.get_full_name", read_only=True)


    class Meta:
        model = Employee
        # fields = "__all__"
        fields = ["id", "user", "name", "role", "joining_date", "base_salary"]
        read_only_fields = ["user"]  
    def get_role(self, obj):
        return [role.name for role in obj.user.role.all()]

    def validate(self, data):
        if data.get('base_salary', 0) <= 0:
            raise serializers.ValidationError({"base_salary": "Amount must be a positive number."})
        
        # Joining date check
        joining_date = data.get("joining_date")
        today = date.today()
        two_months_ago = today - relativedelta(months=2)  # This will take the date of last 2 months

        if joining_date > today:
            raise serializers.ValidationError({"joining_date": "Future date is not allowed."})
        if joining_date < two_months_ago:
            raise serializers.ValidationError({"joining_date": "Joining date cannot be older than 2 months."})



        return data


class EmployeeSalarySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="user.user.get_full_name", read_only=True)
    role = serializers.SerializerMethodField() 
    paid_by_name = serializers.CharField(source="paid_by.get_full_name", read_only=True)
    school_year_name = serializers.SerializerMethodField()  
    user = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())  
    # razorpay_payment_id = serializers.CharField(read_only=True)
    # razorpay_order_id = serializers.CharField(read_only=True)
    # razorpay_signature = serializers.CharField(read_only=True)

    class Meta:
        model = EmployeeSalary
        fields = [
            "id", "user", "employee_name", "role", "gross_amount", "deductions", "net_amount",
            "month","school_year_name", "payment_date", "payment_method",
            "paid_by", "paid_by_name", "remarks", "status", "created_at"]#, "razorpay_payment_id", "razorpay_order_id", "razorpay_signature"]
        extra_kwargs = {
            "net_amount": {"read_only": True},   
            "paid_by": {"read_only": True},
            "gross_amount": {"read_only": True},
            "school_year": {"read_only": True},   
            # "status": {"read_only": True},
            # "payment_method": {"read_only": True},  
            # "month": {"read_only": True},   #  month ab update nahi hoga

        }

    def get_school_year_name(self, obj):   
        return obj.school_year.year_name if obj.school_year else None

    def get_role(self, obj):
        return [role.name for role in obj.user.user.role.all()]

    def validate(self, data):
        user = data.get("user") or getattr(self.instance, "user", None)
        month = data.get("month") or getattr(self.instance, "month", None)
        school_year = data.get("school_year") or getattr(self.instance, "school_year", None)

        qs = EmployeeSalary.objects.filter(user=user, month=month, school_year=school_year)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError("Salary record for this employee for this month already exists.")


        if school_year:
            today = date.today()
            if not (school_year.start_date <= today <= school_year.end_date):
                raise serializers.ValidationError(
                    {"school_year": "You can only create salary records for the current school year."}
                )


        if self.instance and "payment_method" in data:
            raise serializers.ValidationError(
                {"payment_method": "Payment method cannot be changed once created."}
            )
        if self.instance and "deductions" in data:
            raise serializers.ValidationError({"deductions": "Deductions cannot be changed."})

        if self.instance and "month" in data:
            raise serializers.ValidationError({"month": "Month cannot be changed once created."})

        # #Future payment date check
        # if data.get('payment_date') and data['payment_date'] > date.today():
        #     raise serializers.ValidationError({"payment_date": "payment_date cannot be in the future."})
        

        if data.get('payment_date'):

            payment_date = data['payment_date']

            #Future date block
            if payment_date > date.today():
                raise serializers.ValidationError({
                    "payment_date": "Payment date cannot be in the future."
                })

            #School year block 
            if school_year:
                start_year, end_year = map(int, school_year.year_name.split('-'))
                if not (start_year <= payment_date.year <= end_year):
                    raise serializers.ValidationError({
                        "payment_date": f"Payment date must be within the selected school year ({school_year.year_name})."
                    })

            #Extremely old date block
            MIN_YEAR = 2000
            if payment_date.year < MIN_YEAR:
                raise serializers.ValidationError({
                    "payment_date": f"Payment date cannot be earlier than {MIN_YEAR}."
                })


        # Current school year check
        school_year = data.get("school_year") or (self.instance.school_year if self.instance else None)
        if school_year:
            today = date.today()
            if not (school_year.start_date <= today <= school_year.end_date):
                raise serializers.ValidationError(
                    {"school_year": "You can only create salary records for the current school year."}
                )

        # Payment date cannot be before joining date
        if payment_date and payment_date < user.joining_date:
            raise serializers.ValidationError({"payment_date": "Payment date cannot be before joining date."})

        # Month in payment_date must match month field
        if payment_date and month:
            if payment_date.strftime("%B") != month:
                raise serializers.ValidationError({
                    "payment_date": f"Payment date month must match the selected month ({month})."
                })


        # qs = EmployeeSalary.objects.filter(user=user, month=month, school_year=school_year)
        # if self.instance:
        #     qs = qs.exclude(pk=self.instance.pk)

        # if qs.exists():
        #     raise serializers.ValidationError("Salary record for this employee for this month already exists.")

        net_amount = data.get("net_amount", 0)

        deductions = data.get("deductions") or getattr(self.instance, "deductions", 0)
        gross_amount = user.base_salary if user else 0
        data["gross_amount"] = gross_amount
        data["net_amount"] = gross_amount - deductions

        if deductions > gross_amount:
            raise serializers.ValidationError({
                "deductions": f"Deductions ({deductions}) cannot exceed gross salary ({gross_amount})."
            })


        # print(net_amount)
        if data["net_amount"] <= 0 and data.get("payment_method") == "online":
            raise serializers.ValidationError({
                "net_amount": "Net amount must be greater than 0 for online payment."
            })
        print(net_amount)

        return data

    def create(self, validated_data):
        request_user = self.context["request"].user

        # auto-assign current school year 
        today = date.today()
        try:
            current_year = SchoolYear.objects.get(start_date__lte=today, end_date__gte=today)
        except SchoolYear.DoesNotExist:
            raise serializers.ValidationError({"school_year": "No active school year found."})

        validated_data["school_year"] = current_year

        instance = super().create(validated_data)

        if instance.payment_method == "cash":
            instance.status = "paid"
            instance.paid_by = request_user
        elif instance.payment_method in ["cheque", "online"]:
            instance.status = "pending"

        instance.save()
        return instance


    # def update(self, instance, validated_data):
    #     request_user = self.context["request"].user
    #     instance = super().update(instance, validated_data)
    #     if "payment_method" in validated_data and validated_data["payment_method"] != instance.payment_method:
    #         raise serializers.ValidationError(
    #             {"payment_method": "Payment method cannot be changed once set."})

    #     if instance.payment_method == "cheque" and instance.status == "paid" and not instance.paid_by:
    #         instance.paid_by = request_user

    #     if instance.payment_method == "online" and instance.status == "paid" and not instance.paid_by:
    #         instance.paid_by = request_user

    #     instance.save()
    #     return instance

    def update(self, instance, validated_data):
        request_user = self.context["request"].user

        forbidden_fields = ["deductions", "month", "payment_method"]
        for field in forbidden_fields:
            if field in self.initial_data: 
                raise serializers.ValidationError(
                    {field: f"{field} cannot be updated once created."}
                )

        allowed_fields = ["payment_date", "remarks", "status"]
        for field in allowed_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        if instance.status == "paid" and not instance.paid_by:
            instance.paid_by = request_user

        instance.save()
        return instance

class IncomeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = IncomeCategory
        fields = "__all__"

from director.utils import AbsoluteURLFileField
class SchoolIncomeSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    creator = serializers.SerializerMethodField()
    school_year_value = serializers.SerializerMethodField()
    attachment = AbsoluteURLFileField(required=False, allow_null=True)

    class Meta:
        model = SchoolIncome
        fields = "__all__"
        read_only_fields = ["created_at", "creator","school_year_value"]

    def get_creator(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None

    def get_school_year_value(self, obj):
        return obj.school_year.year_name if obj.school_year else None

    def validate_attachment(self, value):
        if not value:
            return value

        # File size check (2 MB max)
        max_size = 2 * 1024 * 1024  # 2 MB
        if value.size > max_size:
            raise serializers.ValidationError("File size must be under 2MB.")

        # File extension check.
        ext = os.path.splitext(value.name)[1].lower()
        allowed_extensions = [".jpg", ".jpeg", ".png", ".webp", ".pdf"]
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"Unsupported file type '{ext}'. Allowed types are: {', '.join(allowed_extensions)}"
            )
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["school_year"] = self.get_school_year_value(instance)
        return data

    def validate(self, data):
        category = data.get("category")
        month = data.get("month")
        school_year = data.get("school_year")
        income_date = data.get("income_date")

        # Ensure amount is positive (skip for Monthly Fees, it gets auto-set later)
        if category and category.name != "Monthly Fees":
            if data.get("amount", 0) <= 0:
                raise serializers.ValidationError({
                    "amount": "Amount must be a positive number."
                })

        # Ensure income date is not in the future
        if income_date and income_date > date.today():
            raise serializers.ValidationError({
                "income_date": "Income date cannot be in the future."
            })

        # Ensure one category per month per school_year
        if category and month and school_year:
            qs = SchoolIncome.objects.filter(
                category=category,
                month=month,
                school_year=school_year
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    "category": f"Income for '{category.name}' already exists for {month} ({school_year})."
                })

        return data

    def create(self, validated_data):
        # Auto-assign creator
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["created_by"] = request.user

        school_year = validated_data["school_year"]   # this is a SchoolYear instance
        month = validated_data["month"]               # pull from validated_data
        category = validated_data.get("category")

        # Auto-set amount for Monthly Fees
        if category and category.name == "Monthly Fees":
            total = (
                FeeRecord.objects.filter(
                    month=month,
                    school_year__year=school_year   # StudentYearLevel.year → SchoolYear
                ).aggregate(total=Sum("paid_amount"))["total"] or 0
            )
            validated_data["amount"] = total

        return super().create(validated_data)
        
    def update(self, instance, validated_data):
        allowed_fields = [
            "amount",
            "description",
            "income_date",
            "payment_method",
            "attachment",
            "status",
        ]

        # block updates for restricted fields (category, school_year, created_by etc.)
        for field in list(validated_data.keys()):
            if field not in allowed_fields:
                validated_data.pop(field)

        # special rule: "Monthly Fees" → amount cannot be updated
        category = instance.category
        if category and category.name == "Monthly Fees":
            validated_data.pop("amount", None)

        return super().update(instance, validated_data)
    

class SchoolTurnOverSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolTurnOver
        fields = [
            "id",
            "school_year",
            "carry_forward",
            "total_income",
            "total_expense",
            "financial_outcome", 
            "financial_status", 
            "net_turnover",
            "calculated_at",
            "is_locked",
            "verified_by",
            "verified_at",
        ]